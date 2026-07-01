import hmac
import hashlib
import base64   
import logging
import json
from app.core.config import settings


logger=logging.getLogger(__name__)
NOMBA_WEBHOOK_SECRET=settings.WEBHOOK_SECRET

def verify_nomba_signature(raw_payload:str, signature_header:str, timestamp:str)->bool:
    try:
        payload=json.loads(raw_payload)
    
        merchant=payload.get("data",{}).get("merchant",{})
        transaction=payload.get("data",{}).get("transaction",{})
    
        response_code=transaction.get("responseCode", "")
        if response_code=="null":
            response_code=""
    
        hashing_payload=":".join([
            payload.get("event_type",""),
            payload.get("requestId",""),
            merchant.get("userId",""),
            merchant.get("walletId",""),
            transaction.get("transactionId",""),
            transaction.get("type",""),
            transaction.get("time",""),
            response_code,
            timestamp
        ])
        logger.info(f"Webhook hashing payload: {hashing_payload}")
        digest=hmac.new(
            NOMBA_WEBHOOK_SECRET.encode(),
            hashing_payload.encode(),
            hashlib.sha256
            ).digest()
         
        expected=base64.b64encode(digest).decode()
        result=hmac.compare_digest(expected, signature_header)
        if not result:
            logger.warning(
                f"Webhook signature verification failed. Expected: {expected}, Received: {signature_header}"
            )
        return result
    except Exception as e:
        logger.error(f"Webhook signature verification failed: {e}")
        return False
    
    