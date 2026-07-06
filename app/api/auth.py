from fastapi import APIRouter, Depends, HTTPException
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.security import get_current_firebase_user
from app.services.user_service import get_or_create_user
from app.schemas.auth import AuthSyncRequest

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/auth/sync")
async def sync_user(
    payload: AuthSyncRequest,
    firebase_user: dict = Depends(get_current_firebase_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        result = await get_or_create_user(
            db=db,
            firebase_uid=firebase_user["uid"],
            email=firebase_user["email"],
            full_name=payload.full_name or firebase_user.get("name") or "New User",
            role_str=payload.role,
            phone=payload.phone
        )
        return result

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        logger.exception(e)
        raise HTTPException(status_code=500, detail="Internal server error")
    
    
    
