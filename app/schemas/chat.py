from typing import Optional
from uuid import UUID

from app.schemas.base import BaseSchema, TimestampSchema
from app.models.message import MessageType, SenderType


class TextMessageIn(BaseSchema):
    session_id: UUID
    content:    str

    @classmethod
    def validate_content(cls, v: str) -> str:
        v = v.strip()
        if len(v) == 0:
            raise ValueError("Message cannot be empty")
        if len(v) > 2000:
            raise ValueError("Message too long — maximum 2000 characters")
        return v


class VoiceMessageIn(BaseSchema):
    session_id: UUID
    audio_url: str


class MessageOut(TimestampSchema):
    session_id:          UUID
    user_id:             UUID
    sender:              SenderType
    msg_type:            MessageType
    content:             Optional[str]   = None

   
    audio_url:           Optional[str]   = None
    transcript:          Optional[str]   = None
    ai_correction:       Optional[str]   = None
    ai_audio_url:        Optional[str]   = None
    pronunciation_score: Optional[float] = None

    is_read:             bool = False


class AIReplyOut(BaseSchema):
   
    message:       str            
    audio_url:     Optional[str] = None  
    correction:    Optional[str] = None   
    used_sources:  Optional[list] = None  