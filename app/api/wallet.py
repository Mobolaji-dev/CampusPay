from fastapi import Depends, HTTPException, APIRouter
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.security import get_current_firebase_user
from sqlalchemy import select
from app.core.database import get_db
from app.models.models import users, wallets, accounts
from app.schemas.wallet import WalletResponse
import logging

logger = logging.getLogger(__name__)


router = APIRouter()

@router.get("/wallet", response_model=WalletResponse)
async def get_wallet(
    firebase_user: dict = Depends(get_current_firebase_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        firebase_uid = firebase_user.get("uid")

        if not firebase_uid:
            raise HTTPException(
                status_code=401,
                detail="Invalid Firebase token",
            )

        query = (
            select(users, wallets, accounts)
            .join(wallets, wallets.user_id == users.user_id)
            .outerjoin(accounts, accounts.student_id == users.user_id)
            .where(users.firebase_uid == firebase_uid)
        )

        result = await db.execute(query)
        row = result.first()

        if not row:
            raise HTTPException(
                status_code=404,
                detail="User or wallet not found",
            )

        user, wallet, account = row

        return WalletResponse(
            user_id=user.user_id,
            role=user.role.value,
            full_name=user.full_name,
            available_balance=wallet.available_balance,
            locked_balance=wallet.locked_balance,
            bank_account_number=account.bank_account_number if account else None,
            bank_name=account.bank_name if account else None,
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.exception(e)
        raise HTTPException(
            status_code=500,
            detail="Internal server error",
        )
    
    
    
    
    
    
  
    
    