from pydantic import BaseModel, field_validator
from decimal import Decimal
from datetime import datetime


class VendorSummary(BaseModel):
    
    vendor_id: str
    name: str
    location: str | None
    phone: str | None
    is_open: bool
    cover_image_url: str | None

    model_config = {"from_attributes": True}


class ProductItem(BaseModel):

    product_id: str
    name: str
    description: str | None
    price: Decimal
    is_available: bool

    model_config = {"from_attributes": True}


class VendorDetail(BaseModel):
    
    vendor_id: str
    name: str
    location: str | None
    phone: str | None
    is_open: bool
    cover_image_url: str | None
    products: list[ProductItem]

    model_config = {"from_attributes": True}


class ProductCreateRequest(BaseModel):
    name: str
    description: str | None = None
    price: Decimal

    @field_validator("price")
    @classmethod
    def validate_price(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("Price must be greater than zero")
        return v


class ProductUpdateRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    price: Decimal | None = None
    is_available: bool | None = None


class ProductResponse(BaseModel):
    product_id: str
    vendor_id: str
    name: str
    description: str | None
    price: Decimal
    is_available: bool
    created_at: datetime

    model_config = {"from_attributes": True}
