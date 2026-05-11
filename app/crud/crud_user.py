from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.base import CRUDBase
from app.models.user import User, UserProfile, UserRole
from app.schemas.auth import RegisterRequest
from app.schemas.user import UserUpdate, UserProfileUpdate
from app.core.security import (
    hash_password,
    generate_secure_token,
    generate_token_expiry,
    is_token_expired,
)


class CRUDUser(CRUDBase[User]):

    #  READ

    async def get_by_id(
        self, db: AsyncSession, user_id: UUID
    ) -> Optional[User]:
        
        result = await db.execute(
            select(User)
            .options(selectinload(User.profile))
            .where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_by_email(
        self, db: AsyncSession, email: str
    ) -> Optional[User]:
        
        result = await db.execute(
            select(User)
            .options(selectinload(User.profile))
            .where(User.email == email.lower().strip())
        )
        return result.scalar_one_or_none()

    async def get_by_verify_token(
        self, db: AsyncSession, token: str
    ) -> Optional[User]:
        
        result = await db.execute(
            select(User).where(User.verify_token == token)
        )
        return result.scalar_one_or_none()

    async def get_by_reset_token(
        self, db: AsyncSession, token: str
    ) -> Optional[User]:
        
        result = await db.execute(
            select(User).where(User.reset_token == token)
        )
        return result.scalar_one_or_none()

    async def email_exists(self, db: AsyncSession, email: str) -> bool:
       
        result = await db.execute(
            select(User.id).where(User.email == email.lower().strip())
        )
        return result.scalar_one_or_none() is not None

    #  CREATE 

    async def create(
        self, db: AsyncSession, data: RegisterRequest
    ) -> User:
        
        role = UserRole.child if (data.age and data.age < 13) else UserRole.learner

        user = User(
            email           = data.email.lower().strip(),
            hashed_password = hash_password(data.password),
            full_name       = data.full_name.strip(),
            age             = data.age,
            role            = role,
            is_active       = True,
            is_verified     = False,
            verify_token    = generate_secure_token(),
        )
        db.add(user)
        await db.flush()  

        profile = UserProfile(user_id=user.id)
        db.add(profile)
        await db.flush()

       
        user.profile = profile
        return user

    # UPDATE 

    async def update(
        self, db: AsyncSession, user: User, data: UserUpdate
    ) -> User:
        
        update_data = data.model_dump(exclude_none=True)
        for field, value in update_data.items():
            setattr(user, field, value)
        db.add(user)
        await db.flush()
        return user

    async def update_profile(
        self, db: AsyncSession, user: User, data: UserProfileUpdate
    ) -> UserProfile:
      
        profile = user.profile
        update_data = data.model_dump(exclude_none=True)
        for field, value in update_data.items():
            setattr(profile, field, value)
        db.add(profile)
        await db.flush()
        return profile

    async def update_password(
        self, db: AsyncSession, user: User, new_plain_password: str
    ) -> User:
        
        user.hashed_password    = hash_password(new_plain_password)
        user.reset_token        = None
        user.reset_token_expires = None
        db.add(user)
        await db.flush()
        return user

    #  EMAIL VERIFICATIOn

    async def verify_email(
        self, db: AsyncSession, user: User
    ) -> User:
       
        user.is_verified  = True
        user.verify_token = None
        db.add(user)
        await db.flush()
        return user

    async def regenerate_verify_token(
        self, db: AsyncSession, user: User
    ) -> User:

        user.verify_token = generate_secure_token()
        db.add(user)
        await db.flush()
        return user


    async def set_reset_token(
        self, db: AsyncSession, user: User
    ) -> str:
       
        token = generate_secure_token()
        user.reset_token         = token
        user.reset_token_expires = generate_token_expiry(hours=1)
        db.add(user)
        await db.flush()
        return token

    async def validate_reset_token(
        self, db: AsyncSession, token: str
    ) -> Optional[User]:
      
        user = await self.get_by_reset_token(db, token)
        if not user:
            return None
        if is_token_expired(user.reset_token_expires):
            return None
        return user

   

    async def deactivate(self, db: AsyncSession, user: User) -> User:
     
        user.is_active = False
        db.add(user)
        await db.flush()
        return user

    async def activate(self, db: AsyncSession, user: User) -> User:
        user.is_active = True
        db.add(user)
        await db.flush()
        return user



crud_user = CRUDUser(User)