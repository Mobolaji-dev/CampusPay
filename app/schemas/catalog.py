from pydantic import BaseModel
from decimal import Decimal


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
