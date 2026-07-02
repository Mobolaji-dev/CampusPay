from fastapi import FastAPI
from app.api import webhooks
from app.core.database import Base, engine
from app.models import models

app = FastAPI(title="CampusPay DVA Infrastructure")

app.include_router(webhooks.router, tags=["Webhooks"])

@app.get("/health")
async def health():
    return {"status": "live", "service": "CampusPay Backend"}

@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)