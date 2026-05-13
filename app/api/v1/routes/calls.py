from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from uuid import UUID
from datetime import datetime, timezone

from app.db.session import get_db
from app.crud.crud_session import crud_session
from app.core.exceptions import (
    NotFoundException,
    PermissionDeniedException,
    BadRequestException,
)
from app.schemas.session import SessionOut, SessionEnd
from app.schemas.auth import MessageResponse
from app.api.deps import get_current_verified_user
from app.models.user import User
from app.models.session import SessionMode

router = APIRouter()

# Only these modes are valid for calls
CALL_MODES = [SessionMode.audio, SessionMode.video]


#  HELPER 

async def _get_call_session(db, session_id, user_id):
   
    session = await crud_session.get_by_id(db, session_id)
    if not session:
        raise NotFoundException("Session")
    if session.user_id != user_id:
        raise PermissionDeniedException()
    if session.mode not in CALL_MODES:
        raise BadRequestException(
            f"Session mode '{session.mode}' is not a call. "
            "Only 'audio' and 'video' sessions support calls."
        )
    return session


#  START CALL 

@router.post("/{session_id}/start", response_model=SessionOut)
async def start_call(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
):
   
    session = await _get_call_session(db, session_id, current_user.id)

    if session.ended_at is not None:
        raise BadRequestException("Cannot start a call that has already ended")

    # Record the precise call start time
    session.started_at = datetime.now(timezone.utc)
    db.add(session)
    await db.commit()
    await db.refresh(session)

    return session


#END CALL 

@router.post("/{session_id}/end", response_model=SessionOut)
async def end_call(
    session_id: UUID,
    data: SessionEnd,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
):
   
    session = await _get_call_session(db, session_id, current_user.id)

    if session.ended_at is not None:
        raise BadRequestException("This call has already ended")

    session = await crud_session.end_session(
        db,
        session,
        duration_s = data.duration_s,
        xp_earned  = data.xp_earned,
    )
    await db.commit()
    await db.refresh(session)

    return session


#CALL STATUS 

@router.get("/{session_id}/status", response_model=SessionOut)
async def get_call_status(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
):
 
    session = await _get_call_session(db, session_id, current_user.id)
    return session


# ACTIVE CALL 

@router.get("/active", response_model=Optional[SessionOut])
async def get_active_call(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
):
   
    session = await crud_session.get_active_session(db, current_user.id)
    if session and session.mode in CALL_MODES:
        return session
    return None


#CALL HISTORY

@router.get("/", response_model=List[SessionOut])
async def get_call_history(
    mode:  Optional[SessionMode] = Query(None, description="Filter: audio | video"),
    skip:  int = Query(default=0,  ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
):
  
    if mode:
        # Validate that the requested mode is a call mode
        if mode not in CALL_MODES:
            raise BadRequestException(
                "Mode filter must be 'audio' or 'video' for call history"
            )
        all_sessions = await crud_session.get_user_sessions_by_mode(
            db, current_user.id, mode
        )
        return all_sessions[skip: skip + limit]
    else:
        from sqlalchemy import select, and_
        from app.models.session import LearningSession

        result = await db.execute(
            select(LearningSession)
            .where(
                and_(
                    LearningSession.user_id == current_user.id,
                    LearningSession.mode.in_(CALL_MODES),
                )
            )
            .order_by(LearningSession.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())


#WEBRTC SIGNAL 

@router.post("/{session_id}/signal", response_model=MessageResponse)
async def send_signal(
    session_id: UUID,
    signal_type: str = Query(..., description="offer | answer | ice-candidate"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
):
  
    session = await _get_call_session(db, session_id, current_user.id)

    if session.ended_at is not None:
        raise BadRequestException("Cannot signal on an ended call")

    valid_types = ["offer", "answer", "ice-candidate"]
    if signal_type not in valid_types:
        raise BadRequestException(
            f"Invalid signal type. Must be one of: {', '.join(valid_types)}"
        )

    return MessageResponse(
        message=f"Signal '{signal_type}' received for session {session_id}. "
                "Real-time exchange handled via Socket.IO."
    )