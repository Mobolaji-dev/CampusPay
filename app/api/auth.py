from fastapi import APIRouter, Depends, HTTPException
from fastapi.requests import Request
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.responses import JSONResponse
from app.core.database import get_db
from app.core.security import get_current_firebase_user
from app.services.user_service import get_or_create_user

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/auth/sync")
async def sync_user(
    request: Request,
    firebase_user: dict = Depends(get_current_firebase_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        body = await request.json()
        result = await get_or_create_user(
            db=db,
            firebase_uid=firebase_user.get("uid"),
            email=firebase_user.get("email"),
            full_name=body.get("full_name"),
            role_str=body.get("role", "student"),
        )
        return JSONResponse(content=result, status_code=200)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Auth sync error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")