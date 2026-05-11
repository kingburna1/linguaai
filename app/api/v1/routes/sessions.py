from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from uuid import UUID

from app.db.session import get_db
from app.crud.crud_session import crud_session
from app.crud.crud_language import crud_language
from app.core.exceptions import NotFoundException, BadRequestException, PermissionDeniedException
from app.schemas.session import SessionCreate, SessionEnd, SessionOut
from app.schemas.auth import MessageResponse
from app.api.deps import get_current_verified_user
from app.models.user import User
from app.models.session import SessionMode

router = APIRouter()


#START SESSION 

@router.post("/start", response_model=SessionOut, status_code=201)
async def start_session(
    data: SessionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
):
 
    # 1. Confirm the language exists and is available
    language = await crud_language.get(db, data.language_id)
    if not language:
        raise NotFoundException("Language")
    if not language.is_available:
        raise BadRequestException(
            f"'{language.name}' is not yet available for learning. "
            "Check back soon — content is being prepared."
        )

    # 2. Force-close any ghost session from a previous crash
    await crud_session.force_close_active(db, current_user.id)

    # 3. Create the new session
    session = await crud_session.create(db, current_user.id, data)
    await db.commit()
    await db.refresh(session)

    return session


#EnD SESSIO

@router.post("/{session_id}/end", response_model=SessionOut)
async def end_session(
    session_id: UUID,
    data: SessionEnd,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
):
   
    session = await crud_session.get_by_id(db, session_id)
    if not session:
        raise NotFoundException("Session")

    # Only the owner can end their sesion
    if session.user_id != current_user.id:
        raise PermissionDeniedException()

   
    if session.ended_at is not None:
        raise BadRequestException("This session has already ended")

    session = await crud_session.end_session(
        db, session, data.duration_s, data.xp_earned
    )
    await db.commit()
    await db.refresh(session)

    return session


#  GET ACTIVE SESSION 

@router.get("/active", response_model=SessionOut | None)
async def get_active_session(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
):
    
    session = await crud_session.get_active_session(db, current_user.id)
    return session  


#  GET SESSION BY ID

@router.get("/{session_id}", response_model=SessionOut)
async def get_session(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
):
  
    session = await crud_session.get_by_id(db, session_id)
    if not session:
        raise NotFoundException("Session")

   
    if session.user_id != current_user.id:
        raise PermissionDeniedException()

    return session


# GET SESSION HISTORY 

@router.get("/", response_model=List[SessionOut])
async def get_session_history(
    skip:  int = Query(default=0,  ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
):
   
    sessions = await crud_session.get_user_sessions(
        db, current_user.id, skip, limit
    )
    return sessions


#GET SESSIONS BY LANGUAGE

@router.get("/language/{language_id}", response_model=List[SessionOut])
async def get_sessions_by_language(
    language_id: UUID,
    skip:  int = Query(default=0,  ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
):
  
    language = await crud_language.get(db, language_id)
    if not language:
        raise NotFoundException("Language")

    sessions = await crud_session.get_user_sessions_by_language(
        db, current_user.id, language_id, skip, limit
    )
    return sessions

# GET SESSIONS BY MODE 

@router.get("/mode/{mode}", response_model=List[SessionOut])
async def get_sessions_by_mode(
    mode: SessionMode,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
):
    sessions = await crud_session.get_user_sessions_by_mode(
        db, current_user.id, mode
    )
    return sessions


#  GET SESSION COUNT 

@router.get("/stats/count", response_model=dict)
async def get_session_count(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
):
    
    count = await crud_session.count_user_sessions(db, current_user.id)
    return {"total_sessions": count, "user_id": str(current_user.id)}