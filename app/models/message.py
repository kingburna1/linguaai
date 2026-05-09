import uuid
from sqlalchemy import Column, String, Boolean, Text, ForeignKey, Float, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import enum

from app.db.base import Base


class MessageType(str, enum.Enum):
    text  = "text"   
    voice = "voice" 


class SenderType(str, enum.Enum):
    user = "user"
    ai   = "ai"


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id  = Column(UUID(as_uuid=True), ForeignKey("learning_sessions.id", ondelete="CASCADE"), nullable=False)
    user_id     = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    sender      = Column(SAEnum(SenderType), nullable=False)
    msg_type    = Column(SAEnum(MessageType), default=MessageType.text, nullable=False)

    
    content     = Column(Text, nullable=True)  


    audio_url          = Column(String(500), nullable=True)  
    transcript         = Column(Text,        nullable=True)   
    ai_correction      = Column(Text,        nullable=True)   
    ai_audio_url       = Column(String(500), nullable=True)   
    pronunciation_score = Column(Float,      nullable=True)   

    is_read     = Column(Boolean, default=False)

    session = relationship("LearningSession", back_populates="messages")
    user    = relationship("User", back_populates="messages")

    def __repr__(self):
        return f"<Message {self.sender} | {self.msg_type} | session={self.session_id}>"