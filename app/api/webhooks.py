
import json
import logging
from decimal import Decimal
from datetime import datetime, timezone

from fastapi import Request, Depends, APIRouter, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.database import get_db
from app.core.security_webhook import verify_nomba_signature
from app.models.models import webhook_events, accounts, wallets, hookstate, wallet_ledger

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/webhook/nomba")
async def nomba_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    try:
        raw_body = await request.body()


        signature = (
            request.headers.get("nomba-signature")
            or request.headers.get("nomba-sig-value")
            or ""
        )
        timestamp = request.headers.get("nomba-timestamp") or ""

        if not signature or not timestamp:
            logger.warning(
                "webhook_missing_signature headers=%s",
                dict(request.headers),
            )
            raise HTTPException(status_code=400, detail="Missing signature or timestamp")

        is_valid = verify_nomba_signature(raw_body.decode(), signature, timestamp)
        if not is_valid:
            logger.warning("webhook_invalid_signature received=%s", signature[:20])
            raise HTTPException(status_code=401, detail="Invalid webhook signature")

        
        try:
            payload = json.loads(raw_body.decode())
        except json.JSONDecodeError:
            logger.error("webhook_malformed_json body=%s", raw_body[:200])
            raise HTTPException(status_code=400, detail="Malformed JSON payload")

        
        event_id = payload.get("requestId") or payload.get("request_id")
        if not event_id:
            logger.error("webhook_missing_request_id payload=%s", str(payload)[:300])
            raise HTTPException(status_code=400, detail="Missing requestId — cannot guarantee idempotency")

        event_type = payload.get("event_type", "unknown")

        logger.info(
            "webhook_received",
            extra={"event_id": event_id, "event_type": event_type},
        )

       
        if event_type != "payment_success":
            logger.info(
                "webhook_unhandled_event event_id=%s event_type=%s",
                event_id,
                event_type,
            )
           
            await _store_unhandled_event(db, event_id, event_type, payload)
            return JSONResponse(content={"message": f"Event type '{event_type}' acknowledged"}, status_code=200)

        
        try:
            transaction_data = payload["data"]["transaction"]
            account_reference = transaction_data["aliasAccountReference"]
            amount = transaction_data["transactionAmount"]
        except KeyError as e:
            logger.error("webhook_malformed_payload missing_field=%s event_id=%s", e, event_id)
            raise HTTPException(status_code=400, detail=f"Malformed webhook payload: missing {e}")

        
        dva_result = await db.execute(
            select(accounts).where(accounts.account_reference == account_reference)
        )
        dva = dva_result.scalar_one_or_none()
        if not dva:
            logger.warning("webhook_unknown_account_reference ref=%s event_id=%s", account_reference, event_id)
            return JSONResponse(content={"message": "Account reference not found"}, status_code=200)

        wallet_result = await db.execute(
            select(wallets).where(wallets.user_id == dva.student_id)
        )
        wallet = wallet_result.scalar_one_or_none()
        if not wallet:
            logger.warning("webhook_wallet_not_found student_id=%s event_id=%s", dva.student_id, event_id)
            return JSONResponse(content={"message": "Wallet not found"}, status_code=200)

        
        credit_amount = Decimal(str(amount))
        balance_before = wallet.available_balance

        new_event = webhook_events(
            event_id=event_id,
            event_type=event_type,
            account_reference=account_reference,
            amount=credit_amount,
            status=hookstate.processed,
            raw_payload=payload,
        )
        db.add(new_event)

        wallet.available_balance += credit_amount
        wallet.updated_at = datetime.now(timezone.utc)

       
        ledger_entry = wallet_ledger(
            wallet_id=wallet.wallet_id,
            user_id=dva.student_id,
            direction="credit",
            amount=credit_amount,
            balance_before=balance_before,
            balance_after=wallet.available_balance,
            reference=event_id,
            order_id=None,
            reason="webhook_credit",
        )
        db.add(ledger_entry)

        try:
            await db.commit()
        except IntegrityError:
            await db.rollback()
            logger.info("webhook_duplicate_ignored event_id=%s", event_id)
            return JSONResponse(content={"message": "Already processed"}, status_code=200)

        logger.info(
            "webhook_wallet_credited",
            extra={
                "event_id": event_id,
                "student_id": dva.student_id,
                "amount": str(credit_amount),
                "balance_before": str(balance_before),
                "balance_after": str(wallet.available_balance),
            },
        )
        return JSONResponse(content={"message": "Webhook processed"}, status_code=200)

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.exception("webhook_processing_error error=%s", e)
        raise HTTPException(status_code=500, detail="Internal Server Error")


async def _store_unhandled_event(
    db: AsyncSession,
    event_id: str,
    event_type: str,
    payload: dict,
) -> None:
   
    try:
        existing = await db.execute(
            select(webhook_events).where(webhook_events.event_id == event_id)
        )
        if existing.scalar_one_or_none():
            return

        event = webhook_events(
            event_id=event_id,
            event_type=event_type,
            account_reference="",
            amount=Decimal("0"),
            status=hookstate.processed,
            raw_payload=payload,
        )
        db.add(event)
        await db.commit()
    except IntegrityError:
        await db.rollback()
    except Exception as exc:
        await db.rollback()
        logger.error("webhook_store_unhandled_error event_id=%s error=%s", event_id, exc)