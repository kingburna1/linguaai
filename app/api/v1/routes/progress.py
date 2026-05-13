from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from uuid import UUID

from app.db.session import get_db
from app.crud.crud_progress import crud_progress
from app.crud.crud_language import crud_language
from app.core.exceptions import NotFoundException
from app.schemas.progress import ProgressOut, ProgressSummary, AchievementOut
from app.api.deps import get_current_verified_user
from app.models.user import User

router = APIRouter()


# ── GET ALL PROGRESS (HOME SCREEN) ────────────────────────────────────────────

@router.get("/", response_model=List[ProgressSummary])
async def get_all_progress(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
):
    """
    Returns a summary card for every language the user is learning.
    Used on the home screen to show all active languages at a glance.

    Example response:
        [
            { "language_name": "French", "total_xp": 150, "streak_days": 5 },
            { "language_name": "Yoruba", "total_xp": 40,  "streak_days": 1 },
        ]
    """
    all_progress = await crud_progress.get_all_by_user(db, current_user.id)

    # Enrich each progress with the language name and flag
    summaries = []
    for p in all_progress:
        language = await crud_language.get(db, p.language_id)
        summaries.append(
            ProgressSummary(
                language_id    = p.language_id,
                language_name  = language.name       if language else None,
                language_flag  = language.flag_emoji if language else None,
                total_xp       = p.total_xp,
                streak_days    = p.streak_days,
                total_sessions = p.total_sessions,
            )
        )
    return summaries


# ── GET PROGRESS FOR ONE LANGUAGE ─────────────────────────────────────────────

@router.get("/{language_id}", response_model=ProgressOut)
async def get_language_progress(
    language_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
):
    """
    Returns full progress details for a specific language.
    Used on the per-language dashboard page showing all stats + achievements.
    """
    language = await crud_language.get(db, language_id)
    if not language:
        raise NotFoundException("Language")

    progress = await crud_progress.get_by_user_and_language(
        db, current_user.id, language_id
    )
    if not progress:
        raise NotFoundException(
            f"No progress found for '{language.name}'. "
            "Start a learning session to begin tracking."
        )
    return progress


# ── INITIALIZE PROGRESS ───────────────────────────────────────────────────────

@router.post("/{language_id}/init", response_model=ProgressOut, status_code=201)
async def init_progress(
    language_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
):
    """
    Creates a fresh progress record for a language if one doesn't exist.
    Called automatically when a user starts their first session in a language.
    Can also be called manually from the language selection screen.
    Safe to call multiple times — never creates duplicates.
    """
    language = await crud_language.get(db, language_id)
    if not language:
        raise NotFoundException("Language")

    progress = await crud_progress.get_or_create(db, current_user.id, language_id)
    await db.commit()
    await db.refresh(progress)
    return progress


# ── RECORD SESSION COMPLETION ─────────────────────────────────────────────────

@router.post("/{language_id}/record-session", response_model=ProgressOut)
async def record_session_completion(
    language_id: UUID,
    xp: int = 10,
    duration_mins: int = 0,
    words_learned: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
):
    """
    Updates progress after a learning session ends.
    Called by the frontend when the user clicks "End Session".

    What it does:
      1. Adds XP earned during the session
      2. Updates the daily streak
      3. Records new words learned
      4. Checks and unlocks any newly earned achievements
      5. Returns updated progress + list of newly unlocked achievements

    Query params:
        xp            — experience points earned this session (default 10)
        duration_mins — how long the session lasted in minutes
        words_learned — vocabulary words encountered this session
    """
    language = await crud_language.get(db, language_id)
    if not language:
        raise NotFoundException("Language")

    # Get or create progress for this language
    progress = await crud_progress.get_or_create(db, current_user.id, language_id)

    # 1. Add XP and session count
    progress = await crud_progress.add_session_xp(db, progress, xp, duration_mins)

    # 2. Update streak
    progress = await crud_progress.update_streak(db, progress)

    # 3. Record vocabulary
    if words_learned > 0:
        progress = await crud_progress.add_words_learned(db, progress, words_learned)

    # 4. Check achievements
    newly_unlocked = await crud_progress.check_and_unlock_achievements(db, progress)

    await db.commit()
    await db.refresh(progress)

    # Log newly unlocked achievements for debugging
    if newly_unlocked:
        names = [a.title for a in newly_unlocked]
        print(f"🏆 User {current_user.id} unlocked: {names}")

    return progress


# ── GET ACHIEVEMENTS ───────────────────────────────────────────────────────────

@router.get("/{language_id}/achievements", response_model=List[AchievementOut])
async def get_achievements(
    language_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
):
    """
    Returns all achievements for a language — both locked and unlocked.
    Used on the achievements/badges screen.
    Locked achievements are shown greyed out to motivate the user.
    """
    progress = await crud_progress.get_by_user_and_language(
        db, current_user.id, language_id
    )
    if not progress:
        raise NotFoundException(
            "No progress found. Start a learning session first."
        )
    return progress.achievements


# ── GET UNLOCKED ACHIEVEMENTS ONLY ────────────────────────────────────────────

@router.get("/{language_id}/achievements/unlocked", response_model=List[AchievementOut])
async def get_unlocked_achievements(
    language_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
):
    """
    Returns only the achievements the user has already earned.
    Used for the trophy shelf / celebration screen.
    """
    progress = await crud_progress.get_by_user_and_language(
        db, current_user.id, language_id
    )
    if not progress:
        raise NotFoundException(
            "No progress found. Start a learning session first."
        )
    return [a for a in progress.achievements if a.is_unlocked]


# ── LEADERBOARD (TOP LEARNERS BY XP) ──────────────────────────────────────────

@router.get("/{language_id}/leaderboard", response_model=List[ProgressSummary])
async def get_leaderboard(
    language_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
):
    """
    Returns the top 10 learners for a specific language ranked by XP.
    Used on the language page to show a competitive leaderboard.
    Motivates users — especially children — to keep learning.
    """
    from sqlalchemy import select
    from app.models.progress import UserProgress

    language = await crud_language.get(db, language_id)
    if not language:
        raise NotFoundException("Language")

    result = await db.execute(
        select(UserProgress)
        .where(UserProgress.language_id == language_id)
        .order_by(UserProgress.total_xp.desc())
        .limit(10)
    )
    top_progress = list(result.scalars().all())

    return [
        ProgressSummary(
            language_id    = p.language_id,
            language_name  = language.name,
            language_flag  = language.flag_emoji,
            total_xp       = p.total_xp,
            streak_days    = p.streak_days,
            total_sessions = p.total_sessions,
        )
        for p in top_progress
    ]