import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.models import approles, products, users
from app.schemas.catalog import ProductItem, VendorDetail, VendorSummary

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/catalog", tags=["catalog"])


@router.get(
    "/vendors",
    response_model=list[VendorSummary],
    summary="List all vendors",
    description=(
        "Returns every user with role=vendor. "
        "Optionally filter by `is_open` to show only currently open stores. "
        "Results are ordered: open vendors first, then alphabetically by name."
    ),
)
async def list_vendors(
    is_open: Annotated[
        bool | None,
        Query(description="Filter by open/closed status. Omit for all vendors."),
    ] = None,
    db: AsyncSession = Depends(get_db),
) -> list[VendorSummary]:
   
    try:
        stmt = select(users).where(users.role == approles.Vendor)

        if is_open is not None:
            stmt = stmt.where(users.vendor_is_open == is_open)

        stmt = stmt.order_by(users.vendor_is_open.desc(), users.full_name.asc())

        result = await db.execute(stmt)
        vendor_rows = result.scalars().all()

        return [
            VendorSummary(
                vendor_id=v.user_id,
                name=v.full_name,
                location=v.vendor_location,
                phone=v.phone,
                is_open=v.vendor_is_open,
                cover_image_url=v.vendor_cover_image_url,
            )
            for v in vendor_rows
        ]

    except HTTPException:
        raise  
    except Exception:
        logger.exception("Unexpected error in list_vendors")
        raise HTTPException(
            status_code=500,
            detail="Unable to fetch vendor list. Please try again later.",
        )



@router.get(
    "/vendors/{vendor_id}",
    response_model=VendorDetail,
    summary="Get vendor details + products",
    description=(
        "Returns the full profile of a single vendor along with their product "
        "catalogue. Pass `available_only=true` to restrict products to those "
        "currently in stock."
    ),
)
async def get_vendor(
    vendor_id: Annotated[
        str,
        Path(description="UUID of the vendor (user_id from the users table)"),
    ],
    available_only: Annotated[
        bool,
        Query(description="When true, only return products where is_available=true."),
    ] = False,
    db: AsyncSession = Depends(get_db),
) -> VendorDetail:
    
    try:
        
        vendor_result = await db.execute(
            select(users).where(
                users.user_id == vendor_id,
                users.role == approles.Vendor, 
            )
        )
        vendor = vendor_result.scalar_one_or_none()

        if vendor is None:
            raise HTTPException(
                status_code=404,
                detail=f"Vendor '{vendor_id}' not found.",
            )

        product_stmt = select(products).where(products.vendor_id == vendor_id)

        if available_only:
            product_stmt = product_stmt.where(products.is_available == True)  

        
        product_stmt = product_stmt.order_by(
            products.is_available.desc(),
            products.created_at.desc(),
        )

        product_result = await db.execute(product_stmt)
        product_rows = product_result.scalars().all()

        return VendorDetail(
            vendor_id=vendor.user_id,
            name=vendor.full_name,
            location=vendor.vendor_location,
            phone=vendor.phone,
            is_open=vendor.vendor_is_open,
            cover_image_url=vendor.vendor_cover_image_url,
            products=[
                ProductItem(
                    product_id=p.product_id,
                    name=p.name,
                    description=p.description,
                    price=p.price,
                    is_available=p.is_available,
                )
                for p in product_rows
            ],
        )

    except HTTPException:
        raise
    except Exception:
        logger.exception("Unexpected error in get_vendor vendor_id=%s", vendor_id)
        raise HTTPException(
            status_code=500,
            detail="Unable to fetch vendor details. Please try again later.",
        )
