from datetime import datetime, timedelta, timezone
from typing import Optional, Literal
from uuid import UUID

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings



pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain_password: str) -> str:
    return pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
   
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(user_id: UUID) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload = {
        "sub":  str(user_id),
        "type": "access",
        "exp":  expire,
        "iat":  datetime.now(timezone.utc),  
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(user_id: UUID) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        days=settings.REFRESH_TOKEN_EXPIRE_DAYS
    )
    payload = {
        "sub":  str(user_id),
        "type": "refresh",
        "exp":  expire,
        "iat":  datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_token_pair(user_id: UUID) -> dict:
    return {
        "access_token":  create_access_token(user_id),
        "refresh_token": create_refresh_token(user_id),
        "token_type":    "bearer",
    }




def decode_token(token: str, expected_type: Literal["access", "refresh"]) -> Optional[str]:
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        user_id: Optional[str] = payload.get("sub")
        token_type: Optional[str] = payload.get("type")

        
        if user_id is None or token_type is None:
            return None

       
        if token_type != expected_type:
            return None

        return user_id

    except JWTError:
        return None



import secrets
from datetime import datetime, timedelta, timezone


def generate_secure_token() -> str:
    return secrets.token_hex(32)


def generate_token_expiry(hours: int = 24) -> str:
   
    expiry = datetime.now(timezone.utc) + timedelta(hours=hours)
    return expiry.isoformat()


def is_token_expired(expiry_str: Optional[str]) -> bool:
    if expiry_str is None:
        return True
    try:
        expiry = datetime.fromisoformat(expiry_str)
       
        if expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) > expiry
    except ValueError:
        return True  