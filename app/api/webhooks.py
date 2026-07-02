from fastapi import FastAPI ,Request,Depends, APIRouter
import json

from sqlalchemy.ext.asyncio import AsyncSession 
from app.core.database import get_db
from sqlalchemy import select
from app.core.security_webhook import verify_nomba_signature



router = APIRouter()

@router.post("/webhook/nomba")
async def nomba_webhook(request:Request, db:AsyncSession=Depends(get_db)):
    try:
        raw_body=await request.body()
        signature=request.headers.get("nomba-signature", "")
        timestamp=request.headers.get("nomba-timestamp", "")
        
        if not signature or timestamp:
            raise HTTPException(status_code=400, detail="Missing signature or timestamp")
        
        is_valid=verify_nomba_signature(raw_body.decode(),timestamp,signature)
        if not is_valid:
            raise HTTPException(status_code=400, detail="Invalid signature")
        
        payload=json.loads(raw_body.decode())
        request_id=payload.get("requestId", "")
        event_type=payload.get("event_type", "")
      
        if event_type != "payment_success":
            return JSONResponse(content={"message": "Event type not handled"}, status_code=200)
        
        result=await db.execute(
            select(webhook_event).where(
                Webhook_event.request_id==payload_obj.request_id
                )    
            )
            existing = result.scalar_one_or_none()

            if existing:
                logger.info(f"Duplicate webhook ignored:{request_id}")
                return JSONResponse(content={"message": "Already processed"}, status_code=200)
            
            account_reference=payload["data"]["transaction"]["aliasAccountReference"]
            amount=payload["data"]["transaction"]["reansactionAmount"]
            
            dva_result=await db.execute(
                select("accounts").where(
                    accounts.account_reference==account_reference)
            )
            dva=dva_result.scalar_one_or_none()
            if not dva:
                logger.warning(f"No dva found for reference:{account_reference}")
                return JSONResponse(content={"message": "Account not Found"}, status_code=200)
            update_balance=
            
            
            
        
    
    return{"message":"Webhook received successfully"}
        