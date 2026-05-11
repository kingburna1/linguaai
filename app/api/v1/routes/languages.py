from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from uuid import UUID

from app.db.session import get_db
from app.crud.crud_language import crud_language
from app.core.exceptions import NotFoundException, BadRequestException
from app.schemas.language import LanguageOut, LanguageCreate, LanguageContentOut
from app.schemas.auth import MessageResponse
from app.api.deps import get_current_verified_user, get_current_admin
from app.models.user import User

router = APIRouter()




@router.get("/", response_model=List[LanguageOut])
async def list_languages(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
):
    languages = await crud_language.get_all_available(db)
    return languages


@router.get("/admin/all", response_model=List[LanguageOut])
async def list_all_languages_admin(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
   
    return await crud_language.get_all(db)




@router.get("/{language_id}", response_model=LanguageOut)
async def get_language(
    language_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
):
   
    language = await crud_language.get(db, language_id)
    if not language:
        raise NotFoundException("Language")
    return language


@router.get("/code/{code}", response_model=LanguageOut)
async def get_language_by_code(
    code: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
):
  
    language = await crud_language.get_by_code(db, code)
    if not language:
        raise NotFoundException("Language")
    return language



@router.post("/", response_model=LanguageOut, status_code=201)
async def create_language(
    data: LanguageCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    if await crud_language.code_exists(db, data.code):
        raise BadRequestException(f"Language with code '{data.code}' already exists")

   
    existing = await crud_language.get_by_name(db, data.name)
    if existing:
        raise BadRequestException(f"Language '{data.name}' already exists")

    language = await crud_language.create(db, data)
    await db.commit()
    await db.refresh(language)
    return language



@router.delete("/{language_id}", response_model=MessageResponse)
async def delete_language(
    language_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    
    deleted = await crud_language.delete(db, language_id)
    if not deleted:
        raise NotFoundException("Language")
    await db.commit()
    return MessageResponse(message="Language deleted successfully.")



@router.patch("/{language_id}/toggle-availability", response_model=LanguageOut)
async def toggle_language_availability(
    language_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
   
    language = await crud_language.get(db, language_id)
    if not language:
        raise NotFoundException("Language")

    if language.is_available:
        language = await crud_language.mark_unavailable(db, language)
    else:
        language = await crud_language.mark_available(db, language)

    await db.commit()
    await db.refresh(language)
    return language




@router.get("/{language_id}/content", response_model=List[LanguageContentOut])
async def get_language_content(
    language_id: UUID,
    skip:  int = Query(default=0,  ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
):
  
    language = await crud_language.get(db, language_id)
    if not language:
        raise NotFoundException("Language")

    content = await crud_language.get_content(db, language_id, skip, limit)
    return content


 

@router.get("/{language_id}/content/search", response_model=List[LanguageContentOut])
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

    results = await crud_language.search_content(db, language_id, q, limit)
    return results