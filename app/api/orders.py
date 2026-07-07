import logging
import bcrypt
import jwt
from decimal import Decimal
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from sqlalchemy.orm import aliased
from app.models.models import products as ProductsModel
from app.models.models import approles
from app.core.config import settings
from app.core.database import get_db
from app.core.security import get_current_firebase_user
from app.models.models import users, wallets, orders, orderstat, wallet_ledger
from app.schemas.orders import PlaceOrderRequest, PlaceOrderResponse, ScanQRRequest, PendingTransactionItem, VendorPendingOrderItem
from app.services.nomba import transfer_to_bank, lookup_account, verify_transfer_status

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/orders", tags=["orders"])

PLATFORM_FEE = Decimal("20.00")
QR_ALGORITHM = "HS256"
ORDER_EXPIRY_HOURS = 24


def _write_ledger(
    wallet: wallets,
    user_id: str,
    direction: str,
    amount: Decimal,
    balance_before: Decimal,
    reference: str,
    reason: str,
    order_id: str | None = None,
) -> wallet_ledger:
    """Create a ledger entry for a balance movement."""
    return wallet_ledger(
        wallet_id=wallet.wallet_id,
        user_id=user_id,
        direction=direction,
        amount=amount,
        balance_before=balance_before,
        balance_after=wallet.available_balance,
        reference=reference,
        order_id=order_id,
        reason=reason,
    )




@router.post("", response_model=PlaceOrderResponse, status_code=201)
async def place_order(
    body: PlaceOrderRequest,
    firebase_user: dict = Depends(get_current_firebase_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        firebase_uid = firebase_user.get("uid")

        user_result = await db.execute(
            select(users).where(users.firebase_uid == firebase_uid)
        )
        student = user_result.scalar_one_or_none()

        if not student:
            raise HTTPException(status_code=404, detail="User not found")

        if not student.transaction_pin_hash:
            raise HTTPException(
                status_code=403,
                detail="Transaction PIN not set. Please set a PIN in your profile before placing orders.",
            )

        pin_valid = bcrypt.checkpw(body.pin.encode(), student.transaction_pin_hash.encode())
        if not pin_valid:
            raise HTTPException(status_code=403, detail="Incorrect transaction PIN")

        wallet_result = await db.execute(
            select(wallets)
            .where(wallets.user_id == student.user_id)
            .with_for_update()
        )
        wallet = wallet_result.scalar_one_or_none()

        if not wallet:
            raise HTTPException(status_code=404, detail="Wallet not found")

        vendor_result = await db.execute(
            select(users).where(users.user_id == body.vendor_id)
        )
        vendor = vendor_result.scalar_one_or_none()

        if not vendor:
            raise HTTPException(status_code=404, detail="Vendor not found")

        total_charge = body.item_amount + PLATFORM_FEE
        if wallet.available_balance < total_charge:
            raise HTTPException(
                status_code=402,
                detail=(
                    f"Insufficient balance. Required: ₦{total_charge} "
                    f"(item ₦{body.item_amount} + ₦{PLATFORM_FEE} fee), "
                    f"Available: ₦{wallet.available_balance}"
                ),
            )

        balance_before = wallet.available_balance
        wallet.available_balance -= total_charge
        wallet.locked_balance += total_charge
        wallet.updated_at = datetime.now(timezone.utc)

        expires_at = datetime.now(timezone.utc) + timedelta(hours=ORDER_EXPIRY_HOURS)

        qr_payload = {
            "order_id": None,
            "vendor_id": body.vendor_id,
            "exp": int(expires_at.timestamp()),
        }

        new_order = orders(
            student_id=student.user_id,
            vendor_id=body.vendor_id,
            item_description=body.item_description,
            item_amount=body.item_amount,
            escrow_hold=total_charge,
            order_status=orderstat.pending,
            qr_token="pending",
            timer_expires_at=expires_at,
        )
        db.add(new_order)
        await db.flush()

        qr_payload["order_id"] = new_order.order_id
        signed_token = jwt.encode(qr_payload, settings.SECRET_KEY, algorithm=QR_ALGORITHM)
        new_order.qr_token = signed_token

        db.add(_write_ledger(
            wallet=wallet,
            user_id=student.user_id,
            direction="debit",
            amount=total_charge,
            balance_before=balance_before,
            reference=new_order.order_id,
            reason="order_escrow_lock",
            order_id=new_order.order_id,
        ))

        await db.commit()

        logger.info(
            "order_placed",
            extra={
                "order_id": new_order.order_id,
                "student_id": student.user_id,
                "vendor_id": body.vendor_id,
                "item_amount": str(body.item_amount),
                "total_charge": str(total_charge),
            },
        )

        return PlaceOrderResponse(
            order_id=new_order.order_id,
            qr_token=signed_token,
            timer_expires_at=expires_at,
            total_charged=str(total_charge),
        )

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.exception("place_order_error: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error")




@router.post("/{order_id}/scan", status_code=200)
async def scan_order_qr(
    order_id: str,
    body: ScanQRRequest,
    firebase_user: dict = Depends(get_current_firebase_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        token_data = jwt.decode(body.qr_token, settings.SECRET_KEY, algorithms=[QR_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="QR code has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid QR token")

    token_order_id = token_data.get("order_id")
    token_vendor_id = token_data.get("vendor_id")

    if token_order_id != order_id:
        raise HTTPException(status_code=401, detail="QR token does not match this order")

    
    firebase_uid = firebase_user.get("uid")
    vendor_result = await db.execute(
        select(users).where(users.firebase_uid == firebase_uid)
    )
    vendor = vendor_result.scalar_one_or_none()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")

   
    order_result = await db.execute(
        select(orders).where(orders.order_id == order_id).with_for_update()
    )
    order = order_result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

   
    if order.order_status != orderstat.pending:
        raise HTTPException(
            status_code=409,
            detail=f"Order cannot be confirmed — current status: {order.order_status.value}",
        )

   
    if token_vendor_id != vendor.user_id:
        raise HTTPException(status_code=403, detail="This QR code is not for your store")


    wallet_result = await db.execute(
        select(wallets).where(wallets.user_id == order.student_id).with_for_update()
    )
    wallet = wallet_result.scalar_one_or_none()
    if not wallet:
        raise HTTPException(status_code=404, detail="Student wallet not found")

    if not vendor.vendor_bank_account or not vendor.vendor_bank_code:
        raise HTTPException(
            status_code=422,
            detail="Vendor has not set up bank account details for payouts",
        )


    try:
        lookup_result = await lookup_account(
            account_number=vendor.vendor_bank_account,
            bank_code=str(vendor.vendor_bank_code),
        )
        if lookup_result.get("code") != "00":
            logger.error(
                "recipient_verification_failed order_id=%s vendor_id=%s lookup=%s",
                order_id, vendor.user_id, lookup_result,
            )
            raise HTTPException(
                status_code=422,
                detail="Recipient account verification failed — transfer aborted",
            )
    except HTTPException:
        raise
    except Exception as lookup_err:
        logger.error(
            "recipient_lookup_exception order_id=%s vendor_id=%s error=%s",
            order_id, vendor.user_id, lookup_err,
        )
        raise HTTPException(
            status_code=502,
            detail="Could not verify recipient account — transfer aborted",
        )

    # ── PHASE 1: Release escrow + mark confirmed — commit before Nomba ────
    # locked_balance decreases by the full hold; platform fee is returned
    # to the student since they picked up on time.
    escrow_before = wallet.available_balance
    wallet.locked_balance -= order.escrow_hold
    wallet.available_balance += PLATFORM_FEE
    wallet.updated_at = datetime.now(timezone.utc)
    order.order_status = orderstat.confirmed


    db.add(_write_ledger(
        wallet=wallet,
        user_id=order.student_id,
        direction="credit",
        amount=PLATFORM_FEE,
        balance_before=escrow_before,
        reference=order_id,
        reason="platform_fee_refund",
        order_id=order_id,
    ))

    try:
        await db.commit()
    except Exception as e:
        await db.rollback()
        logger.exception("scan_db_commit_failed order_id=%s error=%s", order_id, e)
        raise HTTPException(status_code=500, detail="Failed to confirm order — please retry")

    logger.info(
        "escrow_released",
        extra={
            "order_id": order_id,
            "student_id": order.student_id,
            "vendor_id": vendor.user_id,
            "escrow_hold": str(order.escrow_hold),
            "platform_fee_refunded": str(PLATFORM_FEE),
        },
    )

    # ── PHASE 2: Nomba transfer — AFTER DB commit ─────────────────────────
    nomba_ref = None
    try:
        nomba_result = await transfer_to_bank(
            amount=order.item_amount,
            account_name=vendor.full_name,
            account_number=vendor.vendor_bank_account,
            bank_code=str(vendor.vendor_bank_code),
            sender_name="CampusPay",
            narration=f"Payment for order {order_id[:8]} — {order.item_description[:40]}",
            merchantTxRef=order_id,  # idempotency key — safe to retry
        )

        if nomba_result.get("code") == "00":
            nomba_ref = nomba_result.get("data", {}).get("transferRef") or order_id
            logger.info(
                "nomba_transfer_success",
                extra={
                    "order_id": order_id,
                    "vendor_id": vendor.user_id,
                    "amount": str(order.item_amount),
                    "merchantTxRef": order_id,
                    "nomba_ref": nomba_ref,
                },
            )
        else:
            logger.error(
                "[ACTION REQUIRED] nomba_transfer_failed",
                extra={
                    "order_id": order_id,
                    "vendor_id": vendor.user_id,
                    "amount": str(order.item_amount),
                    "merchantTxRef": order_id,
                    "nomba_response": str(nomba_result),
                },
            )

    except Exception as e:
        logger.error(
            "[ACTION REQUIRED] nomba_transfer_exception",
            extra={
                "order_id": order_id,
                "vendor_id": vendor.user_id,
                "amount": str(order.item_amount),
                "error": str(e),
            },
        )

    # ── PHASE 3: Store Nomba transfer ref (best-effort) ───────────────────
    if nomba_ref:
        try:
            order.nomba_transfer_ref = nomba_ref
            await db.commit()
        except Exception as e:
            logger.error("save_nomba_ref_failed order_id=%s error=%s", order_id, e)

    return {
        "message": "Order confirmed",
        "order_id": order_id,
        "amount_paid_to_vendor": str(order.item_amount),
        "platform_fee_refunded": str(PLATFORM_FEE),
        "nomba_transfer_ref": nomba_ref,
    }



@router.get("/{order_id}/transfer-status")
async def get_transfer_status(
    order_id: str,
    firebase_user: dict = Depends(get_current_firebase_user),
    db: AsyncSession = Depends(get_db),
):
   
    try:
        firebase_uid = firebase_user.get("uid")
        user_result = await db.execute(
            select(users).where(users.firebase_uid == firebase_uid)
        )
        user = user_result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        order_result = await db.execute(
            select(orders).where(orders.order_id == order_id)
        )
        order = order_result.scalar_one_or_none()
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")

       
        if user.user_id not in (order.student_id, order.vendor_id):
            raise HTTPException(status_code=403, detail="Access denied")

        merchant_tx_ref = order.nomba_transfer_ref or order_id

        try:
            nomba_status = await verify_transfer_status(merchant_tx_ref)
        except Exception as e:
            logger.error("transfer_status_check_failed order_id=%s error=%s", order_id, e)
            raise HTTPException(status_code=502, detail="Could not reach Nomba for transfer status")

        return {
            "order_id": order_id,
            "order_status": order.order_status.value,
            "nomba_transfer_ref": order.nomba_transfer_ref,
            "nomba_transfer_status": nomba_status,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("get_transfer_status_error order_id=%s error=%s", order_id, e)
        raise HTTPException(status_code=500, detail="Internal server error")




@router.get("/pending", response_model=list[PendingTransactionItem])
async def get_pending_transactions(
    firebase_user: dict = Depends(get_current_firebase_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        firebase_uid = firebase_user.get("uid")
        if not firebase_uid:
            raise HTTPException(status_code=401, detail="Invalid Firebase token")

        user_result = await db.execute(
            select(users).where(users.firebase_uid == firebase_uid)
        )
        user = user_result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        vendor_alias = aliased(users)
        student_alias = aliased(users)

        if user.role == approles.Student:
            stmt = (
                select(
                    orders.order_id,
                    orders.item_description.label("name"),
                    orders.item_amount.label("price"),
                    ProductsModel.description.label("description"),
                    vendor_alias.vendor_location.label("location"),
                    vendor_alias.vendor_cover_image_url.label("image_url"),
                    orders.qr_token,
                    orders.created_at,
                    vendor_alias.user_id.label("vendor_id"),
                    vendor_alias.full_name.label("vendor_name"),
                    orders.escrow_hold.label("total_charged"),
                    orders.timer_expires_at.label("timer_expire_at"),
                )
                .join(vendor_alias, vendor_alias.user_id == orders.vendor_id)
                .outerjoin(
                    ProductsModel,
                    (ProductsModel.vendor_id == orders.vendor_id)
                    & (ProductsModel.name == orders.item_description),
                )
                .where(
                    orders.student_id == user.user_id,
                    orders.order_status == orderstat.pending,
                )
                .order_by(orders.created_at.desc())
            )
        elif user.role == approles.Vendor:
            stmt = (
                select(
                    orders.order_id,
                    orders.item_description.label("name"),
                    orders.item_amount.label("price"),
                    ProductsModel.description.label("description"),
                    student_alias.vendor_location.label("location"),
                    student_alias.vendor_cover_image_url.label("image_url"),
                    orders.qr_token,
                    orders.created_at,
                    orders.vendor_id.label("vendor_id"),
                    vendor_alias.full_name.label("vendor_name"),
                    orders.escrow_hold.label("total_charged"),
                    orders.timer_expires_at.label("timer_expire_at"),
                )
                .join(student_alias, student_alias.user_id == orders.student_id)
                .join(vendor_alias, vendor_alias.user_id == orders.vendor_id)
                .outerjoin(
                    ProductsModel,
                    (ProductsModel.vendor_id == orders.vendor_id)
                    & (ProductsModel.name == orders.item_description),
                )
                .where(
                    orders.vendor_id == user.user_id,
                    orders.order_status == orderstat.pending,
                )
                .order_by(orders.created_at.desc())
            )
        else:
            return []

        result = await db.execute(stmt)
        rows = result.fetchall()

        items = []
        for row in rows:
            created_at_utc = row.created_at
            if created_at_utc.tzinfo is None:
                created_at_utc = created_at_utc.replace(tzinfo=timezone.utc)
            created_at_str = created_at_utc.isoformat().replace("+00:00", "Z")

            timer_expire_utc = row.timer_expire_at
            if timer_expire_utc is not None and timer_expire_utc.tzinfo is None:
                timer_expire_utc = timer_expire_utc.replace(tzinfo=timezone.utc)
            timer_expire_str = (
                timer_expire_utc.isoformat().replace("+00:00", "Z") if timer_expire_utc else None
            )

            items.append(
                PendingTransactionItem(
                    order_id=row.order_id,
                    name=row.name,
                    price=str(row.price),
                    description=row.description,
                    location=row.location,
                    image_url=row.image_url,
                    status="pending",
                    qr_token=row.qr_token,
                    created_at=created_at_str,
                    vendor_id=row.vendor_id,
                    vendor_name=row.vendor_name,
                    total_charged=str(row.total_charged),
                    timer_expire_at=timer_expire_str,
                )
            )
        return items

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("get_pending_transactions_error: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error")



@router.get("/vendor/pending", response_model=list[VendorPendingOrderItem])
async def get_vendor_pending_orders(
    firebase_user: dict = Depends(get_current_firebase_user),
    db: AsyncSession = Depends(get_db),
):
    """Return all pending orders for the authenticated vendor, including the buyer's name."""
    try:
        from app.models.models import approles
        from sqlalchemy.orm import aliased

        firebase_uid = firebase_user.get("uid")
        if not firebase_uid:
            raise HTTPException(status_code=401, detail="Invalid Firebase token")

        user_result = await db.execute(
            select(users).where(users.firebase_uid == firebase_uid)
        )
        current_user = user_result.scalar_one_or_none()
        if not current_user:
            raise HTTPException(status_code=404, detail="User not found")

        if current_user.role != approles.Vendor:
            raise HTTPException(status_code=403, detail="Vendor access required")

        student_alias = aliased(users)
        stmt = (
            select(
                orders.order_id,
                orders.item_description,
                orders.item_amount,
                orders.escrow_hold,
                orders.order_status,
                orders.created_at,
                student_alias.full_name.label("student_name"),
            )
            .join(student_alias, student_alias.user_id == orders.student_id)
            .where(
                orders.vendor_id == current_user.user_id,
                orders.order_status == orderstat.pending,
            )
            .order_by(orders.created_at.desc())
        )

        result = await db.execute(stmt)
        rows = result.fetchall()

        items = []
        for row in rows:
            created_at_utc = row.created_at
            if created_at_utc.tzinfo is None:
                created_at_utc = created_at_utc.replace(tzinfo=timezone.utc)
            items.append(
                VendorPendingOrderItem(
                    order_id=row.order_id,
                    item_description=row.item_description,
                    item_amount=str(row.item_amount),
                    escrow_hold=str(row.escrow_hold),
                    student_name=row.student_name,
                    created_at=created_at_utc.isoformat().replace("+00:00", "Z"),
                    order_status=row.order_status.value,
                )
            )
        return items

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("get_vendor_pending_orders_error: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error")