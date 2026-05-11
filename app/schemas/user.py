from pydantic import EmailStr, field_validator
from typing import Optional
from uuid import UUID

from app.schemas.base import BaseSchema, TimestampSchema
from app.models.user import UserRole




class UserProfileOut(TimestampSchema):
    user_id:         UUID
    avatar_url:      Optional[str]  = None
    native_language: Optional[str]  = None
    bio:             Optional[str]  = None
    preferred_voice: str            = "female"
    daily_goal_mins: int            = 15


class UserProfileUpdate(BaseSchema):
    
    avatar_url:      Optional[str] = None
    native_language: Optional[str] = None
    bio:             Optional[str] = None
    preferred_voice: Optional[str] = None
    daily_goal_mins: Optional[int] = None

    @field_validator("daily_goal_mins")
    @classmethod
    def goal_range(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and (v < 5 or v > 480):
            raise ValueError("Daily goal must be between 5 and 480 minutes")
        return v




class UserOut(TimestampSchema):
    email:       EmailStr
    full_name:   str
    age:         Optional[int]  = None
    role:        UserRole
    is_active:   bool
    is_verified: bool
    profile:     Optional[UserProfileOut] = None


class UserUpdate(BaseSchema):
   
    full_name: Optional[str] = None
    age:       Optional[int] = None

    @field_validator("full_name")
    @classmethod
    def name_not_empty(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip()
            if len(v) < 2:
                raise ValueError("Name must be at least 2 characters")
        return v

    @field_validator("age")
    @classmethod
    def age_range(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and (v < 2 or v > 120):
            raise ValueError("Please enter a valid age")
        return v


class ChangePasswordRequest(BaseSchema):
    current_password: str
    new_password:     str
    confirm_password: str

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not any(c.isupper() for c in v):
            raise ValueError("Must contain at least one uppercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Must contain at least one number")
        return v

    @field_validator("confirm_password")
    @classmethod
    def passwords_match(cls, v: str, info) -> str:
        if "new_password" in info.data and v != info.data["new_password"]:
            raise ValueError("Passwords do not match")
        return v