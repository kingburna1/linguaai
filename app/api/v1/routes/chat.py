from fastapi import APIRouter, Depends, BackgroundTasks, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from uuid import UUID

from app.db.session import get_db
from app.crud.crud_message import message as crud_message
from app.crud.crud_session import crud_session
from app.core.exceptions import NotFoundException, PermissionDeniedException, BadRequestException
from app.schemas.chat import TextMessageIn, VoiceMessageIn, MessageOut, AIReplyOut
from app.schemas.auth import MessageResponse
from app.api.deps import get_current_verified_user
from app.models.user import User
from app.models.message import SenderType

router = APIRouter()




@router.post("/text", response_model=MessageOut, status_code=201)
async def send_text_message(
    data: TextMessageIn,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
):
   
    session = await crud_session.get_by_id(db, data.session_id)
    if not session:
        raise NotFoundException("Session")


    if session.user_id != current_user.id:
        raise PermissionDeniedException()

    
    if session.ended_at is not None:
        raise BadRequestException("Cannot send message to an ended session")

    # Create user message
    message = await crud_message.create_text_message(
        db,
        session_id=data.session_id,
        user_id=current_user.id,
        sender=SenderType.user,
        content=data.content,
    )
    await db.commit()
    await db.refresh(message)

    # Generate AI response asynchronously
    background_tasks.add_task(
        process_user_message,
        session_id=data.session_id,
        user_id=current_user.id,
        message_id=message.id,
    )

    return message


#  SEND VOICE MESSAGE 

@router.post("/voice", response_model=MessageOut, status_code=201)
async def send_voice_message(
    data: VoiceMessageIn,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
):
   
    session = await crud_session.get_by_id(db, data.session_id)
    if not session:
        raise NotFoundException("Session")

    # Only the owner can send messages
    if session.user_id != current_user.id:
        raise PermissionDeniedException()

    # Session must be active
    if session.ended_at is not None:
        raise BadRequestException("Cannot send message to an ended session")

    # Create voice message (placeholder - audio_url would come from frontend)
    message = await crud_message.create_voice_message(
        db,
        session_id=data.session_id,
        user_id=current_user.id,
        sender=SenderType.user,
        audio_url="",  # Would be populated by frontend
    )
    await db.commit()
    await db.refresh(message)

    # Process voice: STT → AI response → TTS
    background_tasks.add_task(
        process_voice_message,
        session_id=data.session_id,
        user_id=current_user.id,
        message_id=message.id,
    )

    return message


# ── GET SESSION MESSAGES ───────────────────────────────────────────────────────

@router.get("/{session_id}", response_model=List[MessageOut])
async def get_session_messages(
    session_id: UUID,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
):
   
    session = await crud_session.get_by_id(db, session_id)
    if not session:
        raise NotFoundException("Session")

    # Only the owner can view their session messages
    if session.user_id != current_user.id:
        raise PermissionDeniedException()

    messages = await crud_message.get_session_messages(db, session_id, skip, limit)
    return messages


#  GET UNREAD MESSAGES 

@router.get("/{session_id}/unread", response_model=List[MessageOut])
async def get_unread_messages(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
):
   
    session = await crud_session.get_by_id(db, session_id)
    if not session:
        raise NotFoundException("Session")

    if session.user_id != current_user.id:
        raise PermissionDeniedException()

    unread = await crud_message.get_unread_messages(db, session_id)
    return unread


# MARK MESSAGE AS READ 

@router.patch("/{message_id}/read", response_model=MessageOut)
async def mark_message_as_read(
    message_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
):
   
    message = await crud_message.get_by_id(db, message_id)
    if not message:
        raise NotFoundException("Message")

    # Only the owner can mark their messages as read
    if message.user_id != current_user.id:
        raise PermissionDeniedException()

    message = await crud_message.mark_as_read(db, message)
    await db.commit()
    await db.refresh(message)
    return message




@router.delete("/{session_id}", response_model=MessageResponse)
async def delete_session_messages(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
):
   
    session = await crud_session.get_by_id(db, session_id)
    if not session:
        raise NotFoundException("Session")

    if session.user_id != current_user.id:
        raise PermissionDeniedException()

    count = await crud_message.delete_session_messages(db, session_id)
    await db.commit()

    return MessageResponse(
        message=f"Deleted {count} message(s) from session"
    )




async def process_user_message(
    session_id: UUID,
    user_id: UUID,
    message_id: UUID,
):
    """Process user text message and generate AI response."""
    # TODO: Implement
    # 1. Fetch message content
    # 2. Call LLM service
    # 3. Generate AI text response
    # 4. Store AI message
    pass


async def process_voice_message(
    session_id: UUID,
    user_id: UUID,
    message_id: UUID,
):
    """Process user voice message: STT → LLM → TTS."""
    # TODO: Implement
    # 1. Transcribe audio (STT)
    # 2. Call LLM service
    # 3. Generate AI text response
    # 4. Convert to speech (TTS)
    # 5. Store AI message with audio
    # 6. Calculate pronunciation score
    pass
