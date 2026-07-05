import logging
import bcrypt
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import get_current_firebase_user
from app.models.models import users
from app.schemas.profile import ProfileResponse, SetPinRequest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/profile", tags=["profile"])


@router.get("", response_model=ProfileResponse)
async def get_profile(
    firebase_user: dict = Depends(get_current_firebase_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        firebase_uid = firebase_user.get("uid")

        query = (
            select(users)
            .where(users.firebase_uid == firebase_uid)
        )
        result = await db.execute(query)
        row = result.first()

        if not row:
            raise HTTPException(status_code=404, detail="User profile not found")

        user = row[0]

        return ProfileResponse(
            user_id=user.user_id,
            full_name=user.full_name,
            email=user.email,
            phone=user.phone,
            role=user.role.value,
            has_transaction_pin=user.transaction_pin_hash is not None,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(e)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/set-pin", status_code=200)
async def set_transaction_pin(
    body: SetPinRequest,
    firebase_user: dict = Depends(get_current_firebase_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        firebase_uid = firebase_user.get("uid")

        result = await db.execute(
            select(users).where(users.firebase_uid == firebase_uid)
        )
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        pin_hash = bcrypt.hashpw(body.pin.encode(), bcrypt.gensalt()).decode()
        user.transaction_pin_hash = pin_hash
        await db.commit()

        logger.info(f"Transaction PIN set for user {user.user_id}")
        return {"message": "Transaction PIN set successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(e)
        raise HTTPException(status_code=500, detail="Internal server error")
