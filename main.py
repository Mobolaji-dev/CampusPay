from fastapi import FastAPI

from app.api import auth, webhooks, wallet, profile, orders
from app.core.database import Base, engine
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="CampusPay DVA Infrastructure")

origins = [
  "https://campuspay-web.vercel.app"
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


@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)