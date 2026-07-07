import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from app.api import auth, catalog, webhooks, wallet, profile, orders
from app.core.database import Base, engine, sessionLocal
from app.models.models import orders as Orders, wallets, orderstat
from app.models import models  

logger = logging.getLogger(__name__)


async def expiry_job():
    while True:
        await asyncio.sleep(60)
        try:
            async with sessionLocal() as db:
                result = await db.execute(
                    select(Orders).where(
                        Orders.order_status == orderstat.pending,
                        Orders.timer_expires_at <= datetime.now(timezone.utc).replace(tzinfo=None),
                    )
                )
                expired_orders = result.scalars().all()
                if not expired_orders:
                    continue

                logger.info("Processing %s expired orders", len(expired_orders))

                for order in expired_orders:
                    wallet_result = await db.execute(
                        select(wallets).where(wallets.user_id == order.student_id)
                    )
                    wallet = wallet_result.scalar_one_or_none()
                    if wallet is None:
                        logger.error(
                            "Wallet missing for student %s (order %s)",
                            order.student_id,
                            order.order_id,
                        )
                        continue

                    vendor_result = await db.execute(
                        select(models.users).where(models.users.user_id == order.vendor_id)
                    )
                    vendor = vendor_result.scalar_one_or_none()

                    # ── PHASE 1: durable state first — refund student, release escrow,
                    # mark expired, flag penalty as pending ─────────────────────────
                    wallet.locked_balance -= order.escrow_hold
                    wallet.available_balance += order.item_amount
                    wallet.updated_at = datetime.now(timezone.utc)
                    order.order_status = orderstat.expired
                    order.penalty_status = "pending"  # new column — see note below

                    try:
                        await db.commit()
                    except Exception:
                        await db.rollback()
                        logger.exception(
                            "DB commit failed while expiring order %s — skipping penalty payout this cycle",
                            order.order_id,
                        )
                        continue

                    logger.info("Refunded expired order %s", order.order_id)

                    # ── PHASE 2: attempt Nomba payout — AFTER commit ────────────
                    if not vendor or not vendor.vendor_bank_account or not vendor.vendor_bank_code:
                        logger.error(
                            "[ACTION REQUIRED] Vendor %s has no bank details — "
                            "₦20 no-show penalty for order %s cannot be paid automatically",
                            order.vendor_id, order.order_id,
                        )
                        continue

                    penalty_ref = None
                    try:
                        nomba_result = await transfer_to_bank(
                            amount=Decimal("20.00"),
                            account_name=vendor.full_name,
                            account_number=vendor.vendor_bank_account,
                            bank_code=str(vendor.vendor_bank_code),
                            sender_name="CampusPay",
                            narration=f"No-show penalty — order {order.order_id[:8]}",
                            merchantTxRef=f"penalty-{order.order_id}",  # distinct idempotency key from the original transfer
                        )
                        if nomba_result.get("code") == "00":
                            penalty_ref = nomba_result.get("data", {}).get("transferRef") or f"penalty-{order.order_id}"
                            logger.info("Penalty payout succeeded: order=%s ref=%s", order.order_id, penalty_ref)
                        else:
                            logger.error(
                                "[ACTION REQUIRED] Penalty transfer FAILED for order %s: %s",
                                order.order_id, nomba_result,
                            )
                    except Exception as e:
                        logger.error(
                            "[ACTION REQUIRED] Penalty transfer raised exception for order %s: %s",
                            order.order_id, e,
                        )

                    # ── PHASE 3: best-effort record of the payout ref ───────────
                    if penalty_ref:
                        try:
                            order.penalty_status = "paid"
                            order.penalty_transfer_ref = penalty_ref
                            await db.commit()
                        except Exception as e:
                            logger.error(
                                "Failed to save penalty_transfer_ref for order %s: %s",
                                order.order_id, e,
                            )

        except Exception:
            logger.exception("Expiry background job failed")


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    task = asyncio.create_task(expiry_job())

    yield

    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


app = FastAPI(
    title="CampusPay DVA Infrastructure",
    lifespan=lifespan,
)

origins = [
    "https://campuspay-web.vercel.app",
    "https://campuspay-3f39.onrender.com",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(webhooks.router, tags=["webhooks"])
app.include_router(wallet.router, prefix="/api", tags=["wallet"])
app.include_router(profile.router)
app.include_router(orders.router)
app.include_router(catalog.router)


@app.get("/health")
async def health():
    return {
        "status": "live",
        "service": "CampusPay Backend",
    }