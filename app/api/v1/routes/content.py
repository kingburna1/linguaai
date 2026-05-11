from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from uuid import UUID

from app.db.session import get_db
from app.crud.crud_language import crud_language
from app.core.exceptions import NotFoundException, BadRequestException
from app.schemas.language import LanguageContentOut
from app.api.deps import get_current_verified_user
from app.models.user import User

router = APIRouter()


#  GET CONTENT BY LANGUAGE 

@router.get("/language/{language_id}", response_model=List[LanguageContentOut])
async def get_language_content(
    language_id: UUID,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
):
   
    language = await crud_language.get(db, language_id)
    if not language:
        raise NotFoundException("Language")

    if not language.is_available:
        raise BadRequestException(
            f"Content for '{language.name}' is not yet available. Check back soon!"
        )

    content = await crud_language.get_content(db, language_id, skip, limit)
    return content


#  SEARCH CONTENT 

@router.get("/language/{language_id}/search", response_model=List[LanguageContentOut])
async def search_language_content(
    language_id: UUID,
    q: str = Query(..., min_length=2, description="Search term"),
    limit: int = Query(default=10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
):
   
    language = await crud_language.get(db, language_id)
    if not language:
        raise NotFoundException("Language")

    if not language.is_available:
        raise BadRequestException(
            f"Content for '{language.name}' is not yet available. Check back soon!"
        )

    results = await crud_language.search_content(db, language_id, q, limit)
    return results


# GET CONTENT BY ID 

@router.get("/{content_id}", response_model=LanguageContentOut)
async def get_content_by_id(
    content_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
):
   
    # TODO: Implement fetch single content by ID
    # For now, this is a placeholder showing the expected pattern
    # You'll need to add a get_by_id method to CRUDLanguage or create CRUDContent

    raise NotFoundException("Content")




@router.get("/language/{language_id}/trending", response_model=List[LanguageContentOut])
async def get_trending_content(
    language_id: UUID,
    limit: int = Query(default=10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
):
   
    language = await crud_language.get(db, language_id)
    if not language:
        raise NotFoundException("Language")

    if not language.is_available:
        raise BadRequestException(
            f"Content for '{language.name}' is not yet available. Check back soon!"
        )

    # TODO: Implement trending/top-rated content query
    # This would order by quality_score or similar metric

    content = await crud_language.get_content(db, language_id, 0, limit)
    return content




@router.get("/language/{language_id}/recommended", response_model=List[LanguageContentOut])
async def get_recommended_content(
    language_id: UUID,
    limit: int = Query(default=10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
):
   
    language = await crud_language.get(db, language_id)
    if not language:
        raise NotFoundException("Language")

    if not language.is_available:
        raise BadRequestException(
            f"Content for '{language.name}' is not yet available. Check back soon!"
        )

    # TODO: Implement personalized recommendations based on:
    # - User progress
    # - Learning level
    # - Content quality score
    # - User history

    content = await crud_language.get_content(db, language_id, 0, limit)
    return content
