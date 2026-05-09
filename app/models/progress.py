import uuid
from sqlalchemy import Column, String, Integer, Float, ForeignKey, Text, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


class UserProgress(Base):
    __tablename__ = "user_progress"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id         = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    language_id     = Column(UUID(as_uuid=True), ForeignKey("languages.id"), nullable=False)

    total_xp            = Column(Integer, default=0)   
    streak_days         = Column(Integer, default=0)    
    longest_streak      = Column(Integer, default=0)
    total_sessions      = Column(Integer, default=0)
    total_time_mins     = Column(Integer, default=0)    
    words_learned       = Column(Integer, default=0)
    avg_pronunciation   = Column(Float,   default=0.0) 

    user     = relationship("User", back_populates="progress")
    language = relationship("Language", back_populates="progress")
    achievements = relationship("Achievement", back_populates="progress", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Progress user={self.user_id} lang={self.language_id} xp={self.total_xp}>"


class Achievement(Base):
    
    __tablename__ = "achievements"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    progress_id = Column(UUID(as_uuid=True), ForeignKey("user_progress.id", ondelete="CASCADE"), nullable=False)
    title       = Column(String(100), nullable=False)  
    description = Column(Text,        nullable=True)
    icon        = Column(String(50),  nullable=True)    
    xp_reward   = Column(Integer,     default=0)
    is_unlocked = Column(Boolean,     default=False)

    progress = relationship("UserProgress", back_populates="achievements")