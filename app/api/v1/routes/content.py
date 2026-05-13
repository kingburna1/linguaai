from fastapi import APIRouter, Depends, Query, BackgroundTasks
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from uuid import UUID

from app.db.session import get_db
from app.crud.crud_language import crud_language
from app.models.language import LanguageContent
from app.models.progress import UserProgress
from app.core.exceptions import NotFoundException, BadRequestException
from app.schemas.language import LanguageContentOut
from app.schemas.auth import MessageResponse
from app.api.deps import get_current_verified_user, get_current_admin
from app.models.user import User

router = APIRouter()


# ── HELPER ─────────────────────────────────────────────────────────────────────

async def _get_available_language(db: AsyncSession, language_id: UUID):
    """Shared check — language must exist and be available."""
    language = await crud_language.get(db, language_id)
    if not language:
        raise NotFoundException("Language")
    if not language.is_available:
        raise BadRequestException(
            f"Content for '{language.name}' is not yet available."
        )
    return language


# ── GET CONTENT BY ID ─────────────────────────────────────────────────────────

@router.get("/item/{content_id}", response_model=LanguageContentOut)
async def get_content_by_id(
    content_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
):
    """
    Fetch a single content chunk by its UUID.
    Used when the frontend needs to display a specific piece of content
    e.g. after the RAG pipeline returns a content reference.
    """
    result = await db.execute(
        select(LanguageContent).where(LanguageContent.id == content_id)
    )
    content = result.scalar_one_or_none()
    if not content:
        raise NotFoundException("Content")
    return content


# ── GET CONTENT BY LANGUAGE ────────────────────────────────────────────────────

@router.get("/language/{language_id}", response_model=List[LanguageContentOut])
async def get_language_content(
    language_id: UUID,
    skip:  int = Query(default=0,  ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
):
    """
    Returns paginated content chunks for a language, ordered by quality score.
    This is the raw learning material the AI teaches from.
    """
    await _get_available_language(db, language_id)
    return await crud_language.get_content(db, language_id, skip, limit)


# ── SEARCH CONTENT ─────────────────────────────────────────────────────────────

@router.get("/language/{language_id}/search", response_model=List[LanguageContentOut])
async def search_language_content(
    language_id: UUID,
    q:     str = Query(..., min_length=2, description="Search term"),
    limit: int = Query(default=10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
):
    """
    Keyword search through a language's content titles and body text.
    Will be replaced by FAISS semantic search once the AI layer is built.
    """
    await _get_available_language(db, language_id)
    return await crud_language.search_content(db, language_id, q, limit)


# ── TRENDING CONTENT ───────────────────────────────────────────────────────────

@router.get("/language/{language_id}/trending", response_model=List[LanguageContentOut])
async def get_trending_content(
    language_id: UUID,
    limit: int = Query(default=10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
):
    """
    Returns the highest quality content for a language.
    Ranked by quality_score descending — the scraper and embedder
    assign scores based on content length, source reliability,
    and linguistic richness.
    Top-scoring content is shown first as the default learning material.
    """
    await _get_available_language(db, language_id)

    result = await db.execute(
        select(LanguageContent)
        .where(LanguageContent.language_id == language_id)
        .order_by(LanguageContent.quality_score.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


# ── RECOMMENDED CONTENT ────────────────────────────────────────────────────────

@router.get("/language/{language_id}/recommended", response_model=List[LanguageContentOut])
async def get_recommended_content(
    language_id: UUID,
    limit: int = Query(default=10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
):
    """
    Returns content personalised to this user's level.

    Personalisation logic:
      - Beginner  (xp < 100)   → short chunks, high quality score
      - Intermediate (100–500) → medium chunks, mixed quality
      - Advanced  (xp > 500)   → all chunks, ordered by quality

    Once FAISS is integrated, this will use semantic similarity
    to the user's recent messages for even tighter personalisation.
    """
    await _get_available_language(db, language_id)

    # Get user's XP for this language to determine level
    progress_result = await db.execute(
        select(UserProgress).where(
            UserProgress.user_id     == current_user.id,
            UserProgress.language_id == language_id,
        )
    )
    progress = progress_result.scalar_one_or_none()
    xp = progress.total_xp if progress else 0

    # Build query based on level
    query = select(LanguageContent).where(
        LanguageContent.language_id == language_id
    )

    if xp < 100:
        # Beginner — short, high quality content only
        query = query.where(
            LanguageContent.quality_score >= 0.6
        ).order_by(
            LanguageContent.quality_score.desc()
        )
    elif xp < 500:
        # Intermediate — broader content, still quality-ordered
        query = query.where(
            LanguageContent.quality_score >= 0.3
        ).order_by(
            LanguageContent.quality_score.desc()
        )
    else:
        # Advanced — all content, best quality first
        query = query.order_by(LanguageContent.quality_score.desc())

    result = await db.execute(query.limit(limit))
    return list(result.scalars().all())


# ── TRIGGER INDEXING — ADMIN ───────────────────────────────────────────────────

@router.post("/language/{language_id}/index", response_model=MessageResponse)
async def index_language_content(
    language_id:      UUID,
    background_tasks: BackgroundTasks,
    youtube_ids:      Optional[str] = Query(None, description="Comma-separated YouTube video IDs"),
    db:               AsyncSession  = Depends(get_db),
    current_user:     User          = Depends(get_current_admin),
):
    """
    Admin only — triggers the full RAG indexing pipeline for a language.
    Scrapes Wikipedia + YouTube + indexes into FAISS.
    Runs in the background — returns immediately.

    Example:
        POST /content/language/{id}/index?youtube_ids=abc123,def456
    """
    language = await crud_language.get(db, language_id)
    if not language:
        raise NotFoundException("Language")

    yt_ids = [v.strip() for v in youtube_ids.split(",")] if youtube_ids else []

    async def run_indexing():
        from app.services.ai.rag import rag_service
        from app.db.session import AsyncSessionLocal
        async with AsyncSessionLocal() as index_db:
            result = await rag_service.index_language(
                language_id   = language_id,
                language_name = language.name,
                language_code = language.code,
                youtube_ids   = yt_ids,
                db            = index_db,
            )
            print(f"[Index] Result: {result}")

    background_tasks.add_task(run_indexing)

    return MessageResponse(
        message=f"Indexing started for '{language.name}'. "
                "The language will become available once complete."
    )