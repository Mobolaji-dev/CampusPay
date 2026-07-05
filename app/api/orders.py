import logging
import bcrypt
import jwt
from decimal import Decimal
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.core.database import get_db
from app.core.security import get_current_firebase_user
from app.models.models import users, wallets, orders, orderstat
from app.schemas.orders import PlaceOrderRequest, PlaceOrderResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/orders", tags=["orders"])

PLATFORM_FEE = Decimal("20.00")
QR_ALGORITHM = "HS256"


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
                detail="Transaction PIN not set. Please set a PIN in your profile before placing orders."
            )

        pin_valid = bcrypt.checkpw(
            body.pin.encode(),
            student.transaction_pin_hash.encode()
        )
        if not pin_valid:
            raise HTTPException(status_code=403, detail="Incorrect transaction PIN")

        wallet_result = await db.execute(
            select(wallets).where(wallets.user_id == student.user_id)
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
                detail=f"Insufficient balance. Required: ₦{total_charge} (item ₦{body.item_amount} + ₦{PLATFORM_FEE} fee), Available: ₦{wallet.available_balance}"
            )

        wallet.available_balance -= total_charge
        wallet.locked_balance += total_charge
        wallet.updated_at = datetime.now(timezone.utc)

        expires_at = datetime.now(timezone.utc) + timedelta(hours=24)

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

        await db.commit()

        logger.info(
            f"Order placed: order_id={new_order.order_id}, student={student.user_id}, "
            f"vendor={body.vendor_id}, amount={body.item_amount}, total_charge={total_charge}"
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
        logger.exception(e)
        raise HTTPException(status_code=500, detail="Internal server error")
