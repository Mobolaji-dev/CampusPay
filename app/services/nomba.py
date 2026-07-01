import httpx
from app.core.config import settings
from datetime import datetime, timedelta, timezone


async def fetch_access_token() -> dict:
    async with httpx.AsyncClient() as client:
        res= await client.post(
            "https://api.nomba.com/v1/auth/token/issue",
            headers={
                "Content-Type":"application/json",
                "accountId":settings.ACCOUNT_ID,
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
            "https://api.nomba.com/v1/auth/token/refresh",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type":"application/json",
                "accountId":settings.ACCOUNT_ID,
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
    


