from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.crud.crud_user import crud_user
from app.core.security import verify_password
from app.core.exceptions import (
    BadRequestException,
    UserNotFoundException,
    PermissionDeniedException,
)
from app.schemas.user import (
    UserOut,
    UserUpdate,
    UserProfileUpdate,
    UserProfileOut,
    ChangePasswordRequest,
)
from app.schemas.auth import MessageResponse
from app.api.deps import get_current_user, get_current_verified_user
from app.models.user import User, UserRole
from uuid import UUID

router = APIRouter()


#  GET CURRENT USER

@router.get("/me", response_model=UserOut)
async def get_me(
    current_user: User = Depends(get_current_verified_user),
):
    return current_user


#  UPDATE ACCOUNT 

@router.patch("/me", response_model=UserOut)
async def update_me(
    data: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
):
   
    updated_user = await crud_user.update(db, current_user, data)
    await db.commit()
    await db.refresh(updated_user)
    return updated_user




@router.get("/me/profile", response_model=UserProfileOut)
async def get_my_profile(
    current_user: User = Depends(get_current_verified_user),
):
   
    if not current_user.profile:
        raise UserNotFoundException()
    return current_user.profile




@router.patch("/me/profile", response_model=UserProfileOut)
async def update_my_profile(
    data: UserProfileUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
):
    if not current_user.profile:
        raise UserNotFoundException()

    updated_profile = await crud_user.update_profile(db, current_user, data)
    await db.commit()
    await db.refresh(updated_profile)
    return updated_profile


#  CHANGE PASSWORD 

@router.post("/me/change-password", response_model=MessageResponse)
async def change_password(
    data: ChangePasswordRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
):
    
    if not verify_password(data.current_password, current_user.hashed_password):
        raise BadRequestException("Current password is incorrect")

    await crud_user.update_password(db, current_user, data.new_password)
    await db.commit()

    return MessageResponse(message="Password changed successfully.")



@router.delete("/me", response_model=MessageResponse)
async def delete_my_account(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
):
    
    await crud_user.deactivate(db, current_user)
    await db.commit()
    return MessageResponse(message="Account deactivated successfully.")




@router.get("/{user_id}", response_model=UserOut)
async def get_user_by_id(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
):
   
    if current_user.id != user_id and current_user.role != UserRole.admin:
        raise PermissionDeniedException()

    user = await crud_user.get_by_id(db, user_id)
    if not user:
        raise UserNotFoundException()

    return user