from fastapi import APIRouter, Depends, BackgroundTasks, Query, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from uuid import UUID

from app.db.session import get_db
from app.crud.crud_message import crud_message
from app.crud.crud_session import crud_session
from app.core.exceptions import NotFoundException, PermissionDeniedException, BadRequestException
from app.schemas.chat import TextMessageIn, MessageOut
from app.schemas.auth import MessageResponse
from app.api.deps import get_current_verified_user
from app.models.user import User
from app.models.message import SenderType, MessageType
from app.services.voice_service import upload_voice_message, process_voice_message
from app.tasks.chat_tasks import process_user_message

router = APIRouter()


# ── SEND TEXT MESSAGE ─────────────────────────────────────────────────────────

@router.post("/text", response_model=MessageOut, status_code=201)
async def send_text_message(
    data:             TextMessageIn,
    background_tasks: BackgroundTasks,
    db:               AsyncSession = Depends(get_db),
    current_user:     User         = Depends(get_current_verified_user),
):
    """
    User sends a text message in a chat session.
    The message is saved immediately and the AI reply is generated
    in the background — the user does not wait for the AI.
    The AI reply is pushed via Socket.IO when ready.
    """
    session = await crud_session.get_by_id(db, data.session_id)
    if not session:
        raise NotFoundException("Session")
    if session.user_id != current_user.id:
        raise PermissionDeniedException()
    if session.ended_at is not None:
        raise BadRequestException("Cannot send message to an ended session")

    message = await crud_message.create_text_message(
        db,
        session_id = data.session_id,
        user_id    = current_user.id,
        sender     = SenderType.user,
        content    = data.content,
    )
    await db.commit()
    await db.refresh(message)

    background_tasks.add_task(
        process_user_message,
        session_id = data.session_id,
        user_id    = current_user.id,
        message_id = message.id,
    )
    return message


# ── SEND VOICE MESSAGE ────────────────────────────────────────────────────────

@router.post("/voice", response_model=MessageOut, status_code=201)
async def send_voice_message(
    session_id:       UUID        = Form(...),
    audio:            UploadFile  = File(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db:               AsyncSession = Depends(get_db),
    current_user:     User         = Depends(get_current_verified_user),
):
    """
    User sends a voice message.

    The frontend sends a multipart form with:
        session_id — UUID of the active session
        audio      — the recorded audio file (webm/wav/mp3)

    Flow:
      1. Validate the session
      2. Read the audio bytes from the upload
      3. Upload audio to Supabase → get URL
      4. Save voice message record with the real audio_url
      5. Trigger background processing:
           Whisper STT → LLM → Edge TTS → save AI reply

    The AI correction is pushed via Socket.IO when ready.
    """
    session = await crud_session.get_by_id(db, session_id)
    if not session:
        raise NotFoundException("Session")
    if session.user_id != current_user.id:
        raise PermissionDeniedException()
    if session.ended_at is not None:
        raise BadRequestException("Cannot send message to an ended session")

    # Validate file type
    content_type = audio.content_type or "audio/webm"
    allowed = {"audio/webm", "audio/wav", "audio/mpeg", "audio/ogg", "audio/mp4"}
    if content_type not in allowed:
        raise BadRequestException(
            f"Unsupported audio format: {content_type}. "
            f"Allowed: {', '.join(allowed)}"
        )

    # Read the uploaded audio bytes
    audio_bytes = await audio.read()
    if len(audio_bytes) == 0:
        raise BadRequestException("Audio file is empty")

    # Upload to Supabase immediately — get a real URL
    audio_url = await upload_voice_message(
        audio_bytes  = audio_bytes,
        content_type = content_type,
    )

    # Save the voice message with the real audio_url
    message = await crud_message.create_voice_message(
        db,
        session_id = session_id,
        user_id    = current_user.id,
        sender     = SenderType.user,
        audio_url  = audio_url,   # ← real URL, not empty string
    )
    await db.commit()
    await db.refresh(message)

    # Process in background: STT → LLM → TTS → save AI reply
    background_tasks.add_task(
        process_voice_message,
        message_id = message.id,
        session_id = session_id,
        user_id    = current_user.id,
    )

    return message


# ── GET SESSION MESSAGES ───────────────────────────────────────────────────────

@router.get("/{session_id}", response_model=List[MessageOut])
async def get_session_messages(
    session_id: UUID,
    skip:  int = Query(default=0,   ge=0),
    limit: int = Query(default=50,  ge=1, le=200),
    db:    AsyncSession = Depends(get_db),
    current_user: User  = Depends(get_current_verified_user),
):
    """Returns all messages in a session, oldest first."""
    session = await crud_session.get_by_id(db, session_id)
    if not session:
        raise NotFoundException("Session")
    if session.user_id != current_user.id:
        raise PermissionDeniedException()

    return await crud_message.get_session_messages(db, session_id, skip, limit)


# ── GET UNREAD MESSAGES ────────────────────────────────────────────────────────

@router.get("/{session_id}/unread", response_model=List[MessageOut])
async def get_unread_messages(
    session_id:   UUID,
    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(get_current_verified_user),
):
    """Returns only unread messages in a session."""
    session = await crud_session.get_by_id(db, session_id)
    if not session:
        raise NotFoundException("Session")
    if session.user_id != current_user.id:
        raise PermissionDeniedException()

    return await crud_message.get_unread_messages(db, session_id)


# ── MARK AS READ ───────────────────────────────────────────────────────────────

@router.patch("/{message_id}/read", response_model=MessageOut)
async def mark_message_as_read(
    message_id:   UUID,
    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(get_current_verified_user),
):
    """Marks a message as read."""
    message = await crud_message.get_by_id(db, message_id)
    if not message:
        raise NotFoundException("Message")
    if message.user_id != current_user.id:
        raise PermissionDeniedException()

    message = await crud_message.mark_as_read(db, message)
    await db.commit()
    await db.refresh(message)
    return message


# ── DELETE SESSION MESSAGES ────────────────────────────────────────────────────

@router.delete("/{session_id}", response_model=MessageResponse)
async def delete_session_messages(
    session_id:   UUID,
    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(get_current_verified_user),
):
    """Deletes all messages in a session."""
    session = await crud_session.get_by_id(db, session_id)
    if not session:
        raise NotFoundException("Session")
    if session.user_id != current_user.id:
        raise PermissionDeniedException()

    count = await crud_message.delete_session_messages(db, session_id)
    await db.commit()
    return MessageResponse(message=f"Deleted {count} message(s) from session")