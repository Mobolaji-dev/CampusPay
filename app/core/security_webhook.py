import hmac
import hashlib
import base64   
import logging
import json
from app.core.config import settings


logger=logging.getLogger(__name__)
NOMBA_WEBHOOK_SECRET=settings.WEBHOOK_SECRET

def verify_nomba_signature(raw_payload: str, signature_header: str, timestamp: str) -> bool:
    try:
        payload = json.loads(raw_payload)
    
        merchant = payload.get("data", {}).get("merchant", {}) or {}
        transaction = payload.get("data", {}).get("transaction", {}) or {}
    
        def safe_str(val):
            if val is None or val == "null":
                return ""
            return str(val)
    
        hashing_payload = ":".join([
            safe_str(payload.get("event_type")),
            safe_str(payload.get("requestId") or payload.get("request_id")),
            safe_str(merchant.get("userId")),
            safe_str(merchant.get("walletId")),
            safe_str(transaction.get("transactionId")),
            safe_str(transaction.get("type")),
            safe_str(transaction.get("time")),
            safe_str(transaction.get("responseCode")),
            safe_str(timestamp)
        ])
        logger.info(f"Webhook hashing payload: {hashing_payload}")
        digest = hmac.new(
            NOMBA_WEBHOOK_SECRET.encode(),
            hashing_payload.encode(),
            hashlib.sha256
        ).digest()
         
        expected = base64.b64encode(digest).decode()
        # Nomba developer docs perform case-insensitive comparisons on the signature value
        result = hmac.compare_digest(expected.strip().lower(), signature_header.strip().lower())
        if not result:
            logger.warning(
                f"Webhook signature verification failed. Expected: {expected}, Received: {signature_header}"
            )
        return result
    except Exception as e:
        logger.error(f"Webhook signature verification failed: {e}")
        return False
    
    