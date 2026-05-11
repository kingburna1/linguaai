from uuid import UUID
from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.core.security import decode_token
from app.core.exceptions import InvalidTokenException, AccountDisabledException
from app.crud.crud_user import crud_user
from app.models.user import User, UserRole

bearer_scheme = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    token = credentials.credentials
    user_id = decode_token(token, expected_type="access")

    if not user_id:
        raise InvalidTokenException("Access token is invalid or expired")

    user = await crud_user.get_by_id(db, UUID(user_id))

    if not user:
        raise InvalidTokenException("User belonging to this token no longer exists")

    if not user.is_active:
        raise AccountDisabledException()

    return user


async def get_current_verified_user(
    current_user: User = Depends(get_current_user),
) -> User:
    from app.core.exceptions import EmailNotVerifiedException
    if not current_user.is_verified:
        raise EmailNotVerifiedException()
    return current_user


async def get_current_admin(
    current_user: User = Depends(get_current_verified_user),
) -> User:
    from app.core.exceptions import PermissionDeniedException
    if current_user.role != UserRole.admin:
        raise PermissionDeniedException("Admin access required")
    return current_user