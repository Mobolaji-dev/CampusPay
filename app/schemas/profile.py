from pydantic import BaseModel, field_validator
import re


class ProfileResponse(BaseModel):
    user_id: str
    full_name: str
    email: str
    phone: str | None
    role: str
    has_transaction_pin: bool
    vendor_bank_account: str | None = None
    vendor_bank_code: str | None = None
    vendor_bank_name: str | None = None


class SetPinRequest(BaseModel):
    pin: str

    @field_validator("pin")
    @classmethod
    def validate_pin(cls, v: str) -> str:
        pin = v.strip()
        if not re.fullmatch(r"\d{4}", pin):
            raise ValueError("Transaction PIN must be exactly 4 digits (numbers only).")
        return pin



class BankItem(BaseModel):
    name: str
    code: str



class AccountLookupRequest(BaseModel):
    account_number: str
    bank_code: str



class VendorBankSetupRequest(BaseModel):
    account_number: str
    bank_code: str
    account_name: str   # pre-resolved by frontend via lookup
    bank_name: str      # human-readable bank label (e.g. "Access Bank")

    @field_validator("account_number")
    @classmethod
    def validate_account_number(cls, v: str) -> str:
        acct = v.strip()
        if not re.fullmatch(r"\d{10}", acct):
            raise ValueError("Account number must be exactly 10 digits.")
        return acct
