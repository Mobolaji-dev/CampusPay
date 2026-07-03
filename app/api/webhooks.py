from fastapi import FastAPI ,Request,Depends, APIRouter, HTTPException
import json
import logging
from sqlalchemy.ext.asyncio import AsyncSession 
from app.core.database import get_db
from sqlalchemy import select
from app.core.security_webhook import verify_nomba_signature
from app.models.models import webhook_events, accounts, wallets, hookstate
from fastapi.responses import JSONResponse
from decimal import Decimal
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/webhook/nomba")
async def nomba_webhook(request:Request, db:AsyncSession=Depends(get_db)):
    try:
        raw_body=await request.body()
        signature=request.headers.get("nomba-signature", "")
        timestamp=request.headers.get("nomba-timestamp", "")
        
        if not signature or not timestamp:
            raise HTTPException(status_code=400, detail="Missing signature or timestamp")
        
        is_valid=verify_nomba_signature(raw_body.decode(),signature, timestamp)
        if not is_valid:
            raise HTTPException(status_code=401, detail="Invalid signature")
        
        payload=json.loads(raw_body.decode())
        event_id=payload.get("requestId", "")
        event_type=payload.get("event_type", "")
      
        if event_type != "payment_success":
            return JSONResponse(content={"message": "Event type not handled"}, status_code=200)
        
        result=await db.execute(
            select(webhook_events).where(
                webhook_events.event_id==event_id
                )    
            )
        existing = result.scalar_one_or_none()

        if existing:
            logger.info(f"Duplicate webhook ignored:{event_id}")
            return JSONResponse(content={"message": "Already processed"}, status_code=200)
            
        account_reference=payload["data"]["transaction"]["aliasAccountReference"]
        amount=payload["data"]["transaction"]["transactionAmount"]
            
        dva_result=await db.execute(
            select(accounts).where(
                accounts.account_reference==account_reference)
            )
        dva=dva_result.scalar_one_or_none()
        if not dva:
            logger.warning(f"No dva found for reference:{account_reference}")
            return JSONResponse(content={"message": "Account not Found"}, status_code=200)
        
        wallet_result = await db.execute(
            select(wallets).where(wallets.user_id == dva.student_id)
        )
        wallet = wallet_result.scalar_one_or_none()
        if not wallet:
            logger.warning(f"No wallet found for student:{dva.student_id}")
            return JSONResponse(content={"message": "Wallet not found"}, status_code=200)

        
        new_event = webhook_events(
                event_id=event_id,
                event_type=event_type,
                account_reference=account_reference,
                amount=Decimal(str(amount)),
                status=hookstate.processed,
                raw_payload=payload,
        )
        db.add(new_event)
        wallet.available_balance += Decimal(str(amount))
        wallet.updated_at = datetime.now(timezone.utc)
        await db.commit()
        logger.info(f"Wallet credited: student={dva.student_id}, amount={amount}, ref={event_id}")
        return JSONResponse(content={"message":"Webhook processed"}, status_code=200)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
        