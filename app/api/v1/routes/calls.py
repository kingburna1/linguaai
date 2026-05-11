from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from uuid import UUID
from datetime import datetime, timezone

from app.db.session import get_db
from app.crud.crud_session import crud_session
from app.core.exceptions import NotFoundException, PermissionDeniedException, BadRequestException
from app.schemas.session import SessionOut
from app.schemas.auth import MessageResponse
from app.api.deps import get_current_verified_user
from app.models.user import User
from app.models.session import SessionMode

router = APIRouter()


# INITIATE CALL

@router.post("/{session_id}/start", response_model=SessionOut)
async def start_call(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
):
   
    session = await crud_session.get_by_id(db, session_id)
    if not session:
        raise NotFoundException("Session")

    if session.user_id != current_user.id:
        raise PermissionDeniedException()

    if session.ended_at is not None:
        raise BadRequestException("Cannot start call on an ended session")

    if session.mode not in [SessionMode.audio, SessionMode.video]:
        raise BadRequestException(
            f"Call mode '{session.mode}' does not support voice/video calls"
        )

    
    await db.commit()
    await db.refresh(session)

    return session


# END CALL

@router.post("/{session_id}/end", response_model=SessionOut)
async def end_call(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
):
   
    session = await crud_session.get_by_id(db, session_id)
    if not session:
        raise NotFoundException("Session")

    if session.user_id != current_user.id:
        raise PermissionDeniedException()

    if session.ended_at is not None:
        raise BadRequestException("This call has already ended")

    # End the session/call (duration and XP would be set by client)
    session = await crud_session.end_session(
        db,
        session,
        duration_s=0,  # Would be calculated by client
        xp_earned=0,   # Would be calculated by client
    )
    await db.commit()
    await db.refresh(session)

    return session


# GET CALL STATUS

@router.get("/{session_id}/status", response_model=SessionOut)
async def get_call_status(
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


# GET USER CALL HISTORY

@router.get("/", response_model=List[SessionOut])
async def get_call_history(
    mode: Optional[SessionMode] = Query(None, description="Filter by session mode"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
):
   
    if mode:
        sessions = await crud_session.get_user_sessions_by_mode(
            db, current_user.id, mode
        )
    else:
        sessions = await crud_session.get_user_sessions(
            db, current_user.id, skip, limit
        )

   
    if not mode:
        sessions = [
            s for s in sessions
            if s.mode in [SessionMode.audio, SessionMode.video]
        ]

    return sessions[skip : skip + limit]




@router.get("/active", response_model=Optional[SessionOut])
async def get_active_call(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
):
   
    session = await crud_session.get_active_session(db, current_user.id)

    if session and session.mode in [SessionMode.audio, SessionMode.video]:
        return session

    return None




@router.post("/{session_id}/signal", response_model=MessageResponse)
async def send_signal(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
):
   
    session = await crud_session.get_by_id(db, session_id)
    if not session:
        raise NotFoundException("Session")

    if session.user_id != current_user.id:
        raise PermissionDeniedException()

    # TODO: Implement WebSocket signaling for peer connection
    # This endpoint would be called to initiate WebRTC offer/answer exchange

    return MessageResponse(message="Signal sent. Waiting for peer response.")
