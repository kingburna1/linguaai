from typing import Optional, List
from uuid import UUID
from datetime import datetime, timezone, timedelta

from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.base import CRUDBase
from app.models.progress import UserProgress, Achievement


class CRUDProgress(CRUDBase[UserProgress]):

    #  READ 

    async def get_by_user_and_language(
        self,
        db: AsyncSession,
        user_id: UUID,
        language_id: UUID,
    ) -> Optional[UserProgress]:
        
        result = await db.execute(
            select(UserProgress)
            .options(selectinload(UserProgress.achievements))
            .where(
                and_(
                    UserProgress.user_id     == user_id,
                    UserProgress.language_id == language_id,
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_all_by_user(
        self,
        db: AsyncSession,
        user_id: UUID,
    ) -> List[UserProgress]:
       
        result = await db.execute(
            select(UserProgress)
            .options(selectinload(UserProgress.achievements))
            .where(UserProgress.user_id == user_id)
            .order_by(UserProgress.total_xp.desc())
        )
        return list(result.scalars().all())

    async def get_or_create(
        self,
        db: AsyncSession,
        user_id: UUID,
        language_id: UUID,
    ) -> UserProgress:
       
        progress = await self.get_by_user_and_language(db, user_id, language_id)
        if progress:
            return progress

        progress = UserProgress(
            user_id     = user_id,
            language_id = language_id,
            total_xp          = 0,
            streak_days       = 0,
            longest_streak    = 0,
            total_sessions    = 0,
            total_time_mins   = 0,
            words_learned     = 0,
            avg_pronunciation = 0.0,
        )
        db.add(progress)
        await db.flush()

        await self._seed_achievements(db, progress.id)
        await db.flush()

        return progress

    #  UPDATE 

    async def add_session_xp(
        self,
        db: AsyncSession,
        progress: UserProgress,
        xp: int,
        duration_mins: int,
    ) -> UserProgress:
       
        progress.total_xp        += xp
        progress.total_sessions  += 1
        progress.total_time_mins += duration_mins
        db.add(progress)
        await db.flush()
        return progress

    async def update_streak(
        self,
        db: AsyncSession,
        progress: UserProgress,
    ) -> UserProgress:
       
        now   = datetime.now(timezone.utc)
        today = now.date()

        last_updated = progress.updated_at
        if last_updated.tzinfo is None:
            last_updated = last_updated.replace(tzinfo=timezone.utc)

        last_date = last_updated.date()

        if last_date == today:
            
            pass
        elif last_date == today - timedelta(days=1):
            
            progress.streak_days += 1
            if progress.streak_days > progress.longest_streak:
                progress.longest_streak = progress.streak_days
        else:
            
            progress.streak_days = 1

        db.add(progress)
        await db.flush()
        return progress

    async def add_words_learned(
        self,
        db: AsyncSession,
        progress: UserProgress,
        count: int,
    ) -> UserProgress:
        
        progress.words_learned += count
        db.add(progress)
        await db.flush()
        return progress

    async def update_pronunciation_score(
        self,
        db: AsyncSession,
        progress: UserProgress,
        new_score: float,
    ) -> UserProgress:
       
        if progress.avg_pronunciation == 0.0:
            progress.avg_pronunciation = new_score
        else:
            progress.avg_pronunciation = round(
                (progress.avg_pronunciation + new_score) / 2, 2
            )
        db.add(progress)
        await db.flush()
        return progress

    #  ACHIEVEMENTS 

    async def _seed_achievements(
        self,
        db: AsyncSession,
        progress_id: UUID,
    ) -> None:
        
        defaults = [
            {
                "title":       "First Word! 🎉",
                "description": "Send your first message in a learning session",
                "icon":        "💬",
                "xp_reward":   10,
            },
            {
                "title":       "On a Roll! 🔥",
                "description": "Maintain a 3-day learning streak",
                "icon":        "🔥",
                "xp_reward":   25,
            },
            {
                "title":       "Week Warrior 📅",
                "description": "Maintain a 7-day learning streak",
                "icon":        "📅",
                "xp_reward":   50,
            },
            {
                "title":       "Vocab Builder 📚",
                "description": "Learn 10 new words",
                "icon":        "📚",
                "xp_reward":   20,
            },
            {
                "title":       "Century Club 💯",
                "description": "Reach 100 XP in this language",
                "icon":        "💯",
                "xp_reward":   15,
            },
            {
                "title":       "Dedicated Learner ",
                "description": "Complete 10 learning sessions",
                "icon":        "⭐",
                "xp_reward":   40,
            },
            {
                "title":       "Pronunciation Pro 🎙️",
                "description": "Achieve an average pronunciation score above 80",
                "icon":        "🎙️",
                "xp_reward":   60,
            },
            {
                "title":       "Marathon Learner 🏃",
                "description": "Spend 60 minutes total learning this language",
                "icon":        "🏃",
                "xp_reward":   35,
            },
        ]
        for a in defaults:
            achievement = Achievement(
                progress_id  = progress_id,
                title        = a["title"],
                description  = a["description"],
                icon         = a["icon"],
                xp_reward    = a["xp_reward"],
                is_unlocked  = False,
            )
            db.add(achievement)

    async def check_and_unlock_achievements(
        self,
        db: AsyncSession,
        progress: UserProgress,
    ) -> List[Achievement]:
       
        newly_unlocked: List[Achievement] = []

        for achievement in progress.achievements:
            if achievement.is_unlocked:
                continue  # already earned — skip

            unlocked = False

            if achievement.title.startswith("First Word"):
                unlocked = progress.total_sessions >= 1

            elif achievement.title.startswith("On a Roll"):
                unlocked = progress.streak_days >= 3

            elif achievement.title.startswith("Week Warrior"):
                unlocked = progress.streak_days >= 7

            elif achievement.title.startswith("Vocab Builder"):
                unlocked = progress.words_learned >= 10

            elif achievement.title.startswith("Century Club"):
                unlocked = progress.total_xp >= 100

            elif achievement.title.startswith("Dedicated Learner"):
                unlocked = progress.total_sessions >= 10

            elif achievement.title.startswith("Pronunciation Pro"):
                unlocked = progress.avg_pronunciation >= 80.0

            elif achievement.title.startswith("Marathon Learner"):
                unlocked = progress.total_time_mins >= 60

            if unlocked:
                achievement.is_unlocked = True
                # Award the XP bonus for unlocking
                progress.total_xp += achievement.xp_reward
                db.add(achievement)
                db.add(progress)
                newly_unlocked.append(achievement)

        if newly_unlocked:
            await db.flush()

        return newly_unlocked



crud_progress = CRUDProgress(UserProgress)