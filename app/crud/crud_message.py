from typing import Optional, List
from uuid import UUID

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.base import CRUDBase
from app.models.message import ChatMessage, SenderType, MessageType
from app.schemas.chat import TextMessageIn, VoiceMessageIn


class CRUDMessage(CRUDBase[ChatMessage]):

    #  READ

    async def get_by_id(
        self, db: AsyncSession, message_id: UUID
    ) -> Optional[ChatMessage]:
       
        result = await db.execute(
            select(ChatMessage).where(ChatMessage.id == message_id)
        )
        return result.scalar_one_or_none()

    async def get_session_messages(
        self,
        db: AsyncSession,
        session_id: UUID,
        skip: int = 0,
        limit: int = 100,
    ) -> List[ChatMessage]:
       
        result = await db.execute(
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at.asc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_user_messages(
        self,
        db: AsyncSession,
        user_id: UUID,
        skip: int = 0,
        limit: int = 100,
    ) -> List[ChatMessage]:
       
        result = await db.execute(
            select(ChatMessage)
            .where(ChatMessage.user_id == user_id)
            .order_by(ChatMessage.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_session_messages_by_sender(
        self,
        db: AsyncSession,
        session_id: UUID,
        sender: SenderType,
    ) -> List[ChatMessage]:
       
        result = await db.execute(
            select(ChatMessage)
            .where(
                and_(
                    ChatMessage.session_id == session_id,
                    ChatMessage.sender == sender,
                )
            )
            .order_by(ChatMessage.created_at.asc())
        )
        return list(result.scalars().all())

    async def get_unread_messages(
        self,
        db: AsyncSession,
        session_id: UUID,
    ) -> List[ChatMessage]:
       
        result = await db.execute(
            select(ChatMessage)
            .where(
                and_(
                    ChatMessage.session_id == session_id,
                    ChatMessage.is_read == False,  # noqa: E712
                )
            )
            .order_by(ChatMessage.created_at.asc())
        )
        return list(result.scalars().all())

    #  CREATE

    async def create_text_message(
        self,
        db: AsyncSession,
        session_id: UUID,
        user_id: UUID,
        sender: SenderType,
        content: str,
    ) -> ChatMessage:
       
        message = ChatMessage(
            session_id = session_id,
            user_id    = user_id,
            sender     = sender,
            msg_type   = MessageType.text,
            content    = content,
        )
        db.add(message)
        await db.flush()
        return message

    async def create_voice_message(
        self,
        db: AsyncSession,
        session_id: UUID,
        user_id: UUID,
        sender: SenderType,
        audio_url: str,
        transcript: Optional[str] = None,
    ) -> ChatMessage:
       
        message = ChatMessage(
            session_id = session_id,
            user_id    = user_id,
            sender     = sender,
            msg_type   = MessageType.voice,
            audio_url  = audio_url,
            transcript = transcript,
        )
        db.add(message)
        await db.flush()
        return message

    #  UPDATE

    async def mark_as_read(
        self,
        db: AsyncSession,
        message: ChatMessage,
    ) -> ChatMessage:
       
        message.is_read = True
        db.add(message)
        await db.flush()
        return message

    async def add_ai_correction(
        self,
        db: AsyncSession,
        message: ChatMessage,
        correction: str,
        audio_url: Optional[str] = None,
        pronunciation_score: Optional[float] = None,
    ) -> ChatMessage:
       
        message.ai_correction = correction
        message.ai_audio_url = audio_url
        message.pronunciation_score = pronunciation_score
        db.add(message)
        await db.flush()
        return message

    #  DELETE

    async def delete_session_messages(
        self,
        db: AsyncSession,
        session_id: UUID,
    ) -> int:
       
        from sqlalchemy import func
        result = await db.execute(
            select(func.count(ChatMessage.id)).where(
                ChatMessage.session_id == session_id
            )
        )
        count = result.scalar_one() or 0

        await db.execute(
            select(ChatMessage).where(ChatMessage.session_id == session_id)
        )
        messages = list((await db.execute(
            select(ChatMessage).where(ChatMessage.session_id == session_id)
        )).scalars().all())

        for msg in messages:
            await db.delete(msg)
        await db.flush()

        return count


crud_message = CRUDMessage(ChatMessage)