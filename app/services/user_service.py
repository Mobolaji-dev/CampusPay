import logging
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.models import users, wallets, accounts, approles, accstatus
from app.services.nomba import create_virtual_account

logger = logging.getLogger(__name__)

async def get_or_create_user(
    db: AsyncSession,
    firebase_uid: str,
    email: str,
    full_name: str,
    role_str: str,
    phone: str | None = None,
) -> dict:
   
    result = await db.execute(
        select(users).where(users.firebase_uid == firebase_uid)
    )
    db_user = result.scalar_one_or_none()

    if db_user:
        
        FALLBACK_NAMES = {"CampusPay User", "New User", None, ""}
        updated = False
        if full_name and db_user.full_name in FALLBACK_NAMES:
            db_user.full_name = full_name
            logger.info(f"Updated full_name for user {db_user.user_id} to '{full_name}'")
            updated = True
        if phone and not db_user.phone:
            db_user.phone = phone
            logger.info(f"Updated phone for user {db_user.user_id}")
            updated = True
        if updated:
            await db.commit()

        wallet_result = await db.execute(
            select(wallets).where(wallets.user_id == db_user.user_id)
        )
        wallet = wallet_result.scalar_one_or_none()

        account_result = await db.execute(
            select(accounts).where(accounts.student_id == db_user.user_id)
        )
        account = account_result.scalar_one_or_none()

        return {
            "user_id": db_user.user_id,
            "role": db_user.role.value,
            "full_name": db_user.full_name,
            "bank_account_number": account.bank_account_number if account else None,
            "bank_name": account.bank_name if account else None,
            "available_balance": str(wallet.available_balance) if wallet else "0.00",
        }

    if not role_str:
        raise ValueError(
            "Role is required when registering. "
            "If you already have an account, please log in instead."
        )
    try:
        app_role = approles[role_str.capitalize()]
    except KeyError:
        raise ValueError(f"Invalid role: {role_str}")

    
    new_user = users(
        firebase_uid=firebase_uid,
        role=app_role,
        full_name=full_name or "CampusPay User",
        email=email,
        phone=phone,
    )
    db.add(new_user)
    await db.flush()

    new_wallet = wallets(
        user_id=new_user.user_id,
        available_balance=Decimal("0.00"),
        locked_balance=Decimal("0.00"),
        currency="NGN",
    )
    db.add(new_wallet)

    response_data = {
        "user_id": new_user.user_id,
        "role": new_user.role.value,
        "full_name": new_user.full_name,
        "available_balance": "0.00",
    }

    if app_role == approles.Student:
        account_ref = new_user.user_id
        va_response = await create_virtual_account(
            student_name=full_name,
            account_ref=account_ref,
        )
        if va_response.get("code") == "00":
            va_data = va_response.get("data", {})
            new_account = accounts(
                student_id=new_user.user_id,
                account_reference=account_ref,
                bank_account_number=va_data.get("bankAccountNumber"),
                bank_name=va_data.get("bankName"),
                status=accstatus.active,
            )
            db.add(new_account)
            response_data["bank_account_number"] = va_data.get("bankAccountNumber")
            response_data["bank_name"] = va_data.get("bankName")
        else:
            description = va_response.get("description", "")
            if "sandbox" in description.lower() or "2 sandbox" in description.lower():
                logger.warning(
                    f"Sandbox DVA cap reached for {new_user.user_id}: {description}. "
                    "User created without a bank account — expected in sandbox mode."
                )
            else:
                logger.error(f"VA creation failed for {new_user.user_id}: {va_response}")

    await db.commit()
    return response_data