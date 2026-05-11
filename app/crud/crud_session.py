from typing import Optional, List
from uuid import UUID
from datetime import datetime, timezone

from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.base import CRUDBase
from app.models.session import LearningSession, SessionMode
from app.schemas.session import SessionCreate


class CRUDSession(CRUDBase[LearningSession]):
    #  READ

    async def get_by_id(
        self, db: AsyncSession, session_id: UUID
    ) -> Optional[LearningSession]:
       
        result = await db.execute(
            select(LearningSession)
            .options(selectinload(LearningSession.messages))
            .where(LearningSession.id == session_id)
        )
        return result.scalar_one_or_none()

    async def get_active_session(
        self, db: AsyncSession, user_id: UUID
    ) -> Optional[LearningSession]:
       
        result = await db.execute(
            select(LearningSession)
            .where(
                and_(
                    LearningSession.user_id  == user_id,
                    LearningSession.ended_at == None,  # noqa: E711
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_user_sessions(
        self,
        db: AsyncSession,
        user_id: UUID,
        skip: int = 0,
        limit: int = 20,
    ) -> List[LearningSession]:
        
        result = await db.execute(
            select(LearningSession)
            .where(LearningSession.user_id == user_id)
            .order_by(LearningSession.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_user_sessions_by_language(
        self,
        db: AsyncSession,
        user_id: UUID,
        language_id: UUID,
        skip: int = 0,
        limit: int = 20,
    ) -> List[LearningSession]:
        
        result = await db.execute(
            select(LearningSession)
            .where(
                and_(
                    LearningSession.user_id     == user_id,
                    LearningSession.language_id == language_id,
                )
            )
            .order_by(LearningSession.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_user_sessions_by_mode(
        self,
        db: AsyncSession,
        user_id: UUID,
        mode: SessionMode,
    ) -> List[LearningSession]:
        
        result = await db.execute(
            select(LearningSession)
            .where(
                and_(
                    LearningSession.user_id == user_id,
                    LearningSession.mode    == mode,
                )
            )
            .order_by(LearningSession.created_at.desc())
        )
        return list(result.scalars().all())

    async def count_user_sessions(
        self, db: AsyncSession, user_id: UUID
    ) -> int:
       
        from sqlalchemy import func
        result = await db.execute(
            select(func.count(LearningSession.id))
            .where(LearningSession.user_id == user_id)
        )
        return result.scalar_one() or 0

    #  CREATE

    async def create(
        self,
        db: AsyncSession,
        user_id: UUID,
        data: SessionCreate,
    ) -> LearningSession:
        
        session = LearningSession(
            user_id     = user_id,
            language_id = data.language_id,
            mode        = data.mode,
            started_at  = datetime.now(timezone.utc),
            xp_earned   = 0,
            duration_s  = 0,
        )
        db.add(session)
        await db.flush()
        return session

    #  end session

    async def end_session(
        self,
        db: AsyncSession,
        session: LearningSession,
        duration_s: int,
        xp_earned: int = 0,
    ) -> LearningSession:
       
        session.ended_at   = datetime.now(timezone.utc)
        session.duration_s = duration_s
        session.xp_earned  = xp_earned
        db.add(session)
        await db.flush()
        return session

    # FORCE CLOSE STALE SESSIONS

    async def force_close_active(
        self, db: AsyncSession, user_id: UUID
    ) -> None:
       
        active = await self.get_active_session(db, user_id)
        if active:
            active.ended_at   = datetime.now(timezone.utc)
            active.duration_s = 0   
            db.add(active)
            await db.flush()



crud_session = CRUDSession(LearningSession)