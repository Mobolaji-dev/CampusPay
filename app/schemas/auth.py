from pydantic import BaseModel
from pydantic import field_validator
import re

class AuthSyncRequest(BaseModel):
    full_name: str | None = None
    role: str = "student"
    phone: str | None = None

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, v: str | None) -> str | None:
        if v is None:
            return None
        name = v.strip()
        if not name:
            return None
    
        if not re.fullmatch(r"[A-Za-z\u00C0-\u024F\s'\-]+", name):
            raise ValueError(
                "Name must contain only letters, spaces, hyphens, or apostrophes. "
                "Special characters like @, #, &, numbers etc. are not allowed."
            )
        return name

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str | None) -> str | None:
        if v is None:
            return None
        phone = v.strip()
        if not re.fullmatch(r"^\+?[1-9]\d{7,14}$", phone):
            raise ValueError(
                "Phone number must be a valid international number (e.g. +2348012345678)"
            )
        return phone