from pydantic import BaseModel, field_validator
from decimal import Decimal
from datetime import datetime


class PlaceOrderRequest(BaseModel):
    vendor_id: str
    item_description: str
    item_amount: Decimal
    pin: str

    @field_validator("item_amount")
    @classmethod
    def validate_amount(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("item_amount must be greater than zero")
        return v

    @field_validator("pin")
    @classmethod
    def validate_pin(cls, v: str) -> str:
        v = v.strip()
        if not v.isdigit() or len(v) != 4:
            raise ValueError("PIN must be exactly 4 digits")
        return v


class PlaceOrderResponse(BaseModel):
    order_id: str
    qr_token: str
    timer_expires_at: datetime
    total_charged: str  


class ScanQRRequest(BaseModel):
    qr_token: str


class PendingTransactionItem(BaseModel):
    order_id: str
    name: str
    price: str
    description: str | None = None
    location: str | None = None
    image_url: str | None = None
    status: str = "pending"
    qr_token: str
    created_at: str


class VendorPendingOrderItem(BaseModel):
    order_id: str
    item_description: str
    item_amount: str
    escrow_hold: str
    student_name: str
    created_at: str
    order_status: str

