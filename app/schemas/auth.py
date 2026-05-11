from pydantic import BaseModel, EmailStr, field_validator, model_validator
from typing import Optional
from app.schemas.base import BaseSchema




class RegisterRequest(BaseSchema):
  
    full_name:        str
    email:            EmailStr         
    password:         str
    confirm_password: str
    age:              Optional[int] = None

    @field_validator("full_name")
    @classmethod
    def name_must_not_be_empty(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 2:
            raise ValueError("Full name must be at least 2 characters")
        if len(v) > 100:
            raise ValueError("Full name must be under 100 characters")
        return v

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one number")
        return v

    @field_validator("age")
    @classmethod
    def age_range(cls, v: Optional[int]) -> Optional[int]:
        if v is not None:
            if v < 2:
                raise ValueError("Minimum age is 2")
            if v > 120:
                raise ValueError("Please enter a valid age")
        return v

    @model_validator(mode="after")
    def passwords_match(self) -> "RegisterRequest":
        if self.password != self.confirm_password:
            raise ValueError("Passwords do not match")
        return self




class LoginRequest(BaseSchema):
    email:    EmailStr
    password: str




class TokenResponse(BaseSchema):
   
    access_token:  str
    refresh_token: str
    token_type:    str = "bearer"


class RefreshTokenRequest(BaseSchema):
    refresh_token: str


class TokenPayload(BaseSchema):
    """
    The data encoded inside a JWT token.
    sub = subject = the user's id.
    type = "access" or "refresh" so we can tell them apart.
    """
    sub:  Optional[str] = None
    type: Optional[str] = None




class VerifyEmailRequest(BaseSchema):
    token: str




class ForgotPasswordRequest(BaseSchema):
    email: EmailStr




class ResetPasswordRequest(BaseSchema):
   
    token:            str
    new_password:     str
    confirm_password: str

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one number")
        return v

    @model_validator(mode="after")
    def passwords_match(self) -> "ResetPasswordRequest":
        if self.new_password != self.confirm_password:
            raise ValueError("Passwords do not match")
        return self




class MessageResponse(BaseSchema):
    message: str
    success: bool = True