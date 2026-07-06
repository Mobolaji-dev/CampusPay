import httpx
from app.core.config import settings
from datetime import datetime, timedelta, timezone
from typing import Optional
from decimal import Decimal


async def fetch_access_token() -> dict:
    async with httpx.AsyncClient() as client:
        res= await client.post(
            f"{settings.NOMBA_BASE_URL}/v1/auth/token/issue",
            headers={
                "Content-Type":"application/json",
                "accountId":settings.NOMBA_ACCOUNT_ID,
            },
            json={
                "grant_type":"client_credentials",
                "client_id":settings.NOMBA_CLIENT_ID,
                "client_secret":settings.NOMBA_PRIVATE_KEY,

            },
        )
        result=res.json()
        if result["code"] != "00":
            raise Exception("Authentication failed")

        access_token = result["data"]["access_token"]
        refresh_token = result["data"]["refresh_token"]
        return {"access_token": access_token, "refresh_token": refresh_token}

async def refresh_access_token(access_token: str, refresh_token: str) -> dict:
    async with httpx.AsyncClient() as client:
        res= await client.post(
            f"{settings.NOMBA_BASE_URL}/v1/auth/token/refresh",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type":"application/json",
                "accountId":settings.NOMBA_ACCOUNT_ID,
            },
            json={
                "grant_type":"refresh_token",
                "refresh_token":refresh_token,
            },
        )
        result=res.json()
        if result["code"]!="00":
            raise Exception("Token refresh failed")
        new_access_token=result["data"]["access_token"]
        return {"access_token": new_access_token}
    
    
    
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
            print(f"Token refresh failed: {e}")

    tokens = await fetch_access_token()
    _cached_access_token = tokens["access_token"]
    _cached_refresh_token = tokens["refresh_token"]
    _token_expires_at = datetime.now(timezone.utc) + timedelta(minutes=25)
    return _cached_access_token
    
async def nomba_api_request(method: str , endpoint: str, payload: dict | None = None) -> dict:
    access_token = await get_valid_token()
    async with httpx.AsyncClient() as client:
        response = await client.request(
            method=method,
            url=f"{settings.NOMBA_BASE_URL}{endpoint}",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
                "accountId": settings.NOMBA_ACCOUNT_ID,
            },
            json=payload,
        )
        return response.json()
    
async def create_virtual_account(student_name: str, account_ref: str, expiry_date:datetime= None)->dict:
    return await nomba_api_request(
        method="POST",
        endpoint=f"/v1/accounts/virtual/{settings.NOMBA_SUB_ACCOUNT_ID}",
        
        payload={
            "accountRef":account_ref,
            "accountName":student_name,
            "expiryDate": "2099-12-31 00:00:00",
                }
    )
        
async def transfer_to_bank(amount:Decimal,
                           account_name: str, 
                           account_number:str,
                           bank_code:str, 
                           sender_name:str,
                           narration:str, 
                           merchantTxRef:str
                           )-> dict:
    url = "/v2/transfers/bank"
    return await nomba_api_request(
        method="POST",
        endpoint=url,
        payload = {
            "amount":int(amount * 100),
            "accountNumber": account_number,
            "accountName": account_name,
            "bankCode": bank_code,
            "merchantTxRef":merchantTxRef,
            "senderName":sender_name,
            "narration":narration,
    }
    )



_banks_cache: list[dict] | None = None
_banks_cache_expires_at: datetime | None = None


async def fetch_banks() -> list[dict]:
    """Return all supported Nigerian banks from Nomba, using an in-process cache."""
    global _banks_cache, _banks_cache_expires_at

    if (
        _banks_cache is not None
        and _banks_cache_expires_at is not None
        and datetime.now(timezone.utc) < _banks_cache_expires_at
    ):
        return _banks_cache

    result = await nomba_api_request(method="GET", endpoint="/v1/transfers/banks")

    if result.get("code") != "00":
        raise Exception(f"Failed to fetch bank list: {result}")

    banks: list[dict] = result.get("data", {}).get("banks") or result.get("data", [])
    _banks_cache = banks
    _banks_cache_expires_at = datetime.now(timezone.utc) + timedelta(hours=24)
    return banks


async def lookup_account(account_number: str, bank_code: str) -> dict:
    """Resolve an account number to an account name via Nomba's lookup endpoint."""
    result = await nomba_api_request(
        method="POST",
        endpoint="/v1/transfers/banks/lookup",
        payload={
            "accountNumber": account_number,
            "bankCode": bank_code,
        },
    )
    return result