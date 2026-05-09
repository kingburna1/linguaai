import uuid
from sqlalchemy import Column, String, Integer, Enum as SAEnum, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import enum

from app.db.base import Base


class SessionMode(str, enum.Enum):
    chat  = "chat"   
    audio = "audio" 
    video = "video" 


class LearningSession(Base):
    __tablename__ = "learning_sessions"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id     = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    language_id = Column(UUID(as_uuid=True), ForeignKey("languages.id"), nullable=False)
    mode        = Column(SAEnum(SessionMode), nullable=False)
    started_at  = Column(DateTime(timezone=True), nullable=True)
    ended_at    = Column(DateTime(timezone=True), nullable=True)
    duration_s  = Column(Integer, default=0)   
    xp_earned   = Column(Integer, default=0)   

    user     = relationship("User", back_populates="sessions")
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Session {self.mode} | user={self.user_id}>"