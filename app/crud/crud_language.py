from typing import Optional, List
from uuid import UUID

from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.base import CRUDBase
from app.models.language import Language, LanguageContent
from app.schemas.language import LanguageCreate


class CRUDLanguage(CRUDBase[Language]):

    #  READ

    async def get_all_available(self, db: AsyncSession) -> List[Language]:
       
        result = await db.execute(
            select(Language)
            .where(Language.is_available == True)
            .order_by(Language.name)
        )
        return list(result.scalars().all())

    async def get_all(self, db: AsyncSession) -> List[Language]:
        
        result = await db.execute(
            select(Language).order_by(Language.name)
        )
        return list(result.scalars().all())

    async def get_by_code(
        self, db: AsyncSession, code: str
    ) -> Optional[Language]:
        
        result = await db.execute(
            select(Language).where(Language.code == code.lower())
        )
        return result.scalar_one_or_none()

    async def get_by_name(
        self, db: AsyncSession, name: str
    ) -> Optional[Language]:
        
        result = await db.execute(
            select(Language).where(Language.name.ilike(name.strip()))
        )
        return result.scalar_one_or_none()

    async def code_exists(self, db: AsyncSession, code: str) -> bool:
       
        result = await db.execute(
            select(Language.id).where(Language.code == code.lower())
        )
        return result.scalar_one_or_none() is not None

    #  CREATE 

    async def create(
        self, db: AsyncSession, data: LanguageCreate
    ) -> Language:
       
        language = Language(
            name         = data.name.strip(),
            code         = data.code.lower().strip(),
            native_name  = data.native_name,
            flag_emoji   = data.flag_emoji,
            description  = data.description,
            is_available = False,  
        )
        db.add(language)
        await db.flush()
        return language

    # UPDATE 

    async def mark_available(
        self, db: AsyncSession, language: Language
    ) -> Language:
        
        language.is_available = True
        db.add(language)
        await db.flush()
        return language

    async def mark_unavailable(
        self, db: AsyncSession, language: Language
    ) -> Language:
        
        language.is_available = False
        db.add(language)
        await db.flush()
        return language

    # CONTENT 

    async def get_content(
        self,
        db: AsyncSession,
        language_id: UUID,
        skip: int = 0,
        limit: int = 20,
    ) -> List[LanguageContent]:
        
        result = await db.execute(
            select(LanguageContent)
            .where(LanguageContent.language_id == language_id)
            .order_by(LanguageContent.quality_score.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def search_content(
        self,
        db: AsyncSession,
        language_id: UUID,
        query: str,
        limit: int = 10,
    ) -> List[LanguageContent]:
      
        search_term = f"%{query.strip()}%"
        result = await db.execute(
            select(LanguageContent)
            .where(
                LanguageContent.language_id == language_id,
                or_(
                    LanguageContent.title.ilike(search_term),
                    LanguageContent.content.ilike(search_term),
                )
            )
            .order_by(LanguageContent.quality_score.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def add_content(
        self,
        db: AsyncSession,
        language_id: UUID,
        source_url: Optional[str],
        source_type: Optional[str],
        title: Optional[str],
        content: str,
    ) -> LanguageContent:
      
        chunk = LanguageContent(
            language_id  = language_id,
            source_url   = source_url,
            source_type  = source_type,
            title        = title,
            content      = content,
            quality_score = 0.0,  
        )
        db.add(chunk)
        await db.flush()
        return chunk



crud_language = CRUDLanguage(Language)