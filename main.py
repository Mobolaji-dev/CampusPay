import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from app.api import auth, webhooks, wallet, profile, orders
from app.core.database import Base, engine, AsyncSessionLocal
from app.models.models import orders as Orders, wallets, orderstat
from app.models import models  # noqa: F401 — registers all tables against Base

logger = logging.getLogger(__name__)


async def expiry_job():
    while True:
        await asyncio.sleep(60)
        try:
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(Orders).where(
                        Orders.order_status == orderstat.pending,
                        Orders.timer_expires_at <= datetime.now(timezone.utc),
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

                    wallet.locked_balance -= order.escrow_hold
                    wallet.available_balance += order.item_amount
                    wallet.updated_at = datetime.now(timezone.utc)
                    order.order_status = orderstat.expired

                    # ₦20 penalty owed to vendor — logged for manual ops or future retry queue
                    logger.info(
                        "[ACTION REQUIRED] ₦20 no-show penalty owed to vendor %s "
                        "for expired order %s",
                        order.vendor_id,
                        order.order_id,
                    )

                    logger.info("Refunded expired order %s", order.order_id)

                await db.commit()

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


@app.get("/health")
async def health():
    return {
        "status": "live",
        "service": "CampusPay Backend",
    }