from sqlalchemy import (
    String,
    Integer,
    ForeignKey,
    Text,
    DateTime,
    Numeric,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from decimal import Decimal
from core.database import Base
from enum import Enum
from datetime import datetime, timezone, timedelta
from sqlalchemy import Enum as SAEnum
import uuid


class approles(Enum):
    vendor = "Vendor"
    Student = "Student"
    admin = "Admin"


class accstatus(Enum):
    active = "Active"
    suspended = "Suspended"


class hookstate(Enum):
    processed = "Processed"
    failed = "Failed"
    duplicate = "Duplicate"


class orderstat(Enum):
    pending = "Pending"
    confirmed = "Confirmed"
    expired = "Expired"
    refunded = "Refunded"


class users(Base):

    __tablename__ = "user"

    user_id: Mapped[str] = mapped_column(String, primary_key=True, default= lambda: str(uuid.uuid4()))
    role: Mapped[approles] = mapped_column(SAEnum(approles))
    full_name: Mapped[str] = mapped_column(String)
    email: Mapped[str] = mapped_column(String, unique=True)
    phone: Mapped[str] = mapped_column(String, unique=True)
    vendor_bank_account: Mapped[str | None ] = mapped_column(String, nullable=True)
    vendor_bank_code: Mapped[int | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.now,
    )


class accounts(Base):

    __tablename__ = "account"

    dva_id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda:str(uuid.uuid4()))
    student_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("users.user_id"),
    )
    account_reference: Mapped[str] = mapped_column(Text, unique=True)
    bank_account_number: Mapped[str] = mapped_column(Text)
    bank_name: Mapped[str] = mapped_column(Text)
    status: Mapped[accstatus] = mapped_column(SAEnum(accstatus))
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.now,
    )


class wallets(Base):

    __tablename__ = "wallet"

    wallet_id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda:str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("users.user_id"),
        unique=True,
    )
    available_balance: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    locked_balance: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    currency: Mapped[str] = mapped_column(String(3))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.now,
    )


class webhook_events(Base):

    __tablename__ = "webhookEvents"

    event_id: Mapped[str] = mapped_column(String, primary_key=True)
    event_type: Mapped[str] = mapped_column(String)
    account_reference: Mapped[str] = mapped_column(String)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    status: Mapped[hookstate] = mapped_column(SAEnum(hookstate))
    raw_payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    processed_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.now,
    )


class orders(Base):

    __tablename__ = "order"

    order_id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda:str(uuid.uuid4()))
    student_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("users.user_id"),
    )
    vendor_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("users.user_id"),
    )
    item_description: Mapped[str] = mapped_column(Text)
    item_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    escrow_hold: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    order_status: Mapped[orderstat] = mapped_column(SAEnum(orderstat))
    qr_token: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        unique=True,
    )
    timer_expires_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc) + timedelta(hours=24),
    )
    nomba_transfer_ref: Mapped[str | None] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.now,
    )