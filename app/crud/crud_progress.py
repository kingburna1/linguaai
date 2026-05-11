from typing import Optional, List
from uuid import UUID
from datetime import datetime, timezone

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.base import CRUDBase
from app.models.progress import UserProgress
from app.schemas.progress import ProgressCreate, ProgressUpdate


class CRUDProgress(CRUDBase[UserProgress]):

    #  READ

    async def get_by_user_and_language(
        self, db: AsyncSession, user_id: UUID, language_id: UUID
    ) -> Optional[UserProgress]:
       
        result = await db.execute(
            select(UserProgress).where(
                UserProgress.user_id == user_id,
                UserProgress.language_id == language_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_user_progress(
        self, db: AsyncSession, user_id: UUID
    ) -> List[UserProgress]:
       
        result = await db.execute(
            select(UserProgress).where(UserProgress.user_id == user_id)
        )
        return list(result.scalars().all())

    async def get_user_progress_over_time(
        self, db: AsyncSession, user_id: UUID, language_id: UUID
    ) -> List[UserProgress]:
       
        result = await db.execute(
            select(UserProgress)
            .where(
                UserProgress.user_id == user_id,
                UserProgress.language_id == language_id,
            )
            .order_by(UserProgress.updated_at)
        )
        return list(result.scalars().all())

    async def get_user_progress_summary(
        self, db: AsyncSession, user_id: UUID
    ) -> List:
       
        result = await db.execute(
            select(
                UserProgress.language_id,
                func.max(UserProgress.total_xp).label("max_xp"),
                func.max(UserProgress.updated_at).label("last_updated"),
            )
            .where(UserProgress.user_id == user_id)
            .group_by(UserProgress.language_id)
        )
        return list(result.all())

    async def get_user_progress_for_dashboard(
        self, db: AsyncSession, user_id: UUID
    ) -> List[UserProgress]:
       
        result = await db.execute(
            select(UserProgress)
            .where(UserProgress.user_id == user_id)
            .order_by(UserProgress.updated_at.desc())
            .limit(5)
        )
        return list(result.scalars().all())

    #  CREATE

    async def create(
        self, db: AsyncSession, data: ProgressCreate
    ) -> UserProgress:
       
        progress = UserProgress(**data.dict())
        db.add(progress)
        await db.flush()
        return progress

    #  UPDATE

    async def update(
        self, db: AsyncSession, progress: UserProgress, data: ProgressUpdate
    ) -> UserProgress:
       
        update_data = data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(progress, field, value)
        db.add(progress)
        await db.flush()
        return progress

    async def reset_user_progress(
        self, db: AsyncSession, user_id: UUID, language_id: UUID
    ) -> bool:
       
        progress = await self.get_by_user_and_language(db, user_id, language_id)
        if not progress:
            return False
        progress.total_xp = 0
        progress.streak_days = 0
        progress.total_sessions = 0
        progress.total_time_mins = 0
        progress.words_learned = 0
        progress.avg_pronunciation = 0.0
        progress.updated_at = datetime.now(timezone.utc)
        db.add(progress)
        await db.flush()
        return True

    #  DELETE

    async def delete_by_user_and_language(
        self, db: AsyncSession, user_id: UUID, language_id: UUID
    ) -> bool:
       
        progress = await self.get_by_user_and_language(db, user_id, language_id)
        if not progress:
            return False
        await db.delete(progress)
        await db.flush()
        return True


progress = CRUDProgress(UserProgress)
