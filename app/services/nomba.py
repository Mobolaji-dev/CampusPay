

import time
import httpx
from app.core.config import settings
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import logging


logger = logging.getLogger(__name__)

_TIMEOUT = httpx.Timeout(30.0)  


async def fetch_access_token() -> dict:
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        res = await client.post(
            f"{settings.NOMBA_BASE_URL}/v1/auth/token/issue",
            headers={
                "Content-Type": "application/json",
                "accountId": settings.NOMBA_ACCOUNT_ID,
            },
            json={
                "grant_type": "client_credentials",
                "client_id": settings.NOMBA_CLIENT_ID,
                "client_secret": settings.NOMBA_CLIENT_SECRET,  
            },
        )
        result = res.json()
        if result["code"] != "00":
            raise Exception(f"Nomba authentication failed: {result.get('description', result)}")

        access_token = result["data"]["access_token"]
        refresh_token = result["data"]["refresh_token"]
        return {"access_token": access_token, "refresh_token": refresh_token}


async def refresh_access_token(access_token: str, refresh_token: str) -> dict:
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        res = await client.post(
            f"{settings.NOMBA_BASE_URL}/v1/auth/token/refresh",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
                "accountId": settings.NOMBA_ACCOUNT_ID,
            },
            json={
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
            },
        )
        result = res.json()
        if result["code"] != "00":
            raise Exception(f"Token refresh failed: {result.get('description', result)}")
        return {"access_token": result["data"]["access_token"]}


_cached_access_token: str | None = None
_cached_refresh_token: str | None = None
_token_expires_at: datetime | None = None


async def get_valid_token() -> str:
    
    global _cached_access_token, _cached_refresh_token, _token_expires_at

    if _cached_access_token and _token_expires_at and datetime.now(timezone.utc) < _token_expires_at:
        return _cached_access_token

    if _cached_refresh_token and _cached_access_token:
        try:
            tokens = await refresh_access_token(_cached_access_token, _cached_refresh_token)
            _cached_access_token = tokens["access_token"]
            _token_expires_at = datetime.now(timezone.utc) + timedelta(minutes=25)
            return _cached_access_token
        except Exception as e:
            logger.warning("Nomba token refresh failed, re-authenticating: %s", e)

    tokens = await fetch_access_token()
    _cached_access_token = tokens["access_token"]
    _cached_refresh_token = tokens["refresh_token"]
    _token_expires_at = datetime.now(timezone.utc) + timedelta(minutes=25)
    return _cached_access_token



async def nomba_api_request(method: str, endpoint: str, payload: dict | None = None) -> dict:
   
    access_token = await get_valid_token()
    url = f"{settings.NOMBA_BASE_URL}{endpoint}"
    t0 = time.monotonic()

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:  # H-4
            response = await client.request(
                method=method,
                url=url,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                    "accountId": settings.NOMBA_ACCOUNT_ID,
                },
                json=payload,
            )
            duration_ms = int((time.monotonic() - t0) * 1000)
            result = response.json()

        
            logger.info(
                "nomba_api_call",
                extra={
                    "endpoint": endpoint,
                    "method": method,
                    "http_status": response.status_code,
                    "nomba_code": result.get("code"),
                    "duration_ms": duration_ms,
                },
            )
            return result

    except httpx.TimeoutException:
        duration_ms = int((time.monotonic() - t0) * 1000)
        logger.error(
            "nomba_api_timeout",
            extra={"endpoint": endpoint, "method": method, "duration_ms": duration_ms},
        )
        raise
    except httpx.HTTPError as exc:
        logger.error("nomba_api_http_error: endpoint=%s error=%s", endpoint, exc)
        raise


async def create_virtual_account(student_name: str, account_ref: str) -> dict:
    return await nomba_api_request(
        method="POST",
        endpoint=f"/v1/accounts/virtual/{settings.NOMBA_SUB_ACCOUNT_ID}",
        payload={
            "accountRef": account_ref,
            "accountName": student_name,
            "expiryDate": "2099-12-31 00:00:00",
        },
    )



async def transfer_to_bank(
    amount: Decimal,
    account_name: str,
    account_number: str,
    bank_code: str,
    sender_name: str,
    narration: str,
    merchantTxRef: str,
) -> dict:
   
    logger.info(
        "nomba_transfer_initiate",
        extra={
            "merchantTxRef": merchantTxRef,
            "amount": str(amount),
            "bank_code": bank_code,
            "account_number_tail": account_number[-4:] if account_number else None,
        },
    )
    return await nomba_api_request(
        method="POST",
        endpoint="/v2/transfers/bank",
        payload={
            "amount": float(amount),      
            "accountNumber": account_number,
            "accountName": account_name,
            "bankCode": bank_code,
            "merchantTxRef": merchantTxRef,
            "senderName": sender_name,
            "narration": narration,
        },
    )



async def verify_transfer_status(merchant_tx_ref: str) -> dict:

    logger.info("nomba_transfer_status_check", extra={"merchantTxRef": merchant_tx_ref})
    return await nomba_api_request(
        method="GET",
        endpoint=f"/v2/transfers/{merchant_tx_ref}",
    )


_banks_cache: list[dict] | None = None
_banks_cache_expires_at: datetime | None = None


async def fetch_banks() -> list[dict]:
    
    global _banks_cache, _banks_cache_expires_at

    if (
        _banks_cache is not None
        and _banks_cache_expires_at is not None
        and datetime.now(timezone.utc) < _banks_cache_expires_at
    ):
        return _banks_cache

    result = await nomba_api_request(method="GET", endpoint="/v1/transfers/banks")

    # H-6: was print() — replaced with logger.debug (disabled in production)
    logger.debug("nomba_bank_list_response code=%s", result.get("code"))

    if result.get("code") != "00":
        raise Exception(f"Failed to fetch bank list: {result.get('description', result)}")

    data = result.get("data", [])
    if isinstance(data, list):
        banks = data
    elif isinstance(data, dict):
        banks = data.get("banks", [])
    else:
        banks = []

    _banks_cache = banks
    _banks_cache_expires_at = datetime.now(timezone.utc) + timedelta(hours=24)
    return banks



async def lookup_account(account_number: str, bank_code: str) -> dict:
  
    logger.info(
        "nomba_account_lookup",
        extra={"bank_code": bank_code, "account_tail": account_number[-4:]},
    )
    result = await nomba_api_request(
        method="POST",
        endpoint="/v1/transfers/bank/lookup",
        payload={"accountNumber": account_number, "bankCode": bank_code},
    )
    return result