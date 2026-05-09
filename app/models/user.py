import uuid
from sqlalchemy import Column, String, Boolean, Integer, Enum as SAEnum, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import enum

from app.db.base import Base


class UserRole(str, enum.Enum):
    child   = "child"    
    learner = "learner"  
    parent  = "parent"   
    admin   = "admin"   


class User(Base):
    __tablename__ = "users"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email           = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name       = Column(String(100), nullable=False)
    age             = Column(Integer, nullable=True)   
    role            = Column(SAEnum(UserRole), default=UserRole.learner, nullable=False)
    is_active       = Column(Boolean, default=True)    
    is_verified     = Column(Boolean, default=False)   

    
    reset_token          = Column(String(255), nullable=True)
    reset_token_expires  = Column(String(255), nullable=True) 

  
    verify_token         = Column(String(255), nullable=True)

    
    parent_id       = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

  
    profile         = relationship("UserProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    sessions        = relationship("LearningSession", back_populates="user", cascade="all, delete-orphan")
    messages        = relationship("ChatMessage", back_populates="user", cascade="all, delete-orphan")
    progress        = relationship("UserProgress", back_populates="user", cascade="all, delete-orphan")
    children        = relationship("User", backref="parent", foreign_keys=[parent_id])

    def __repr__(self):
        return f"<User {self.email} | {self.role}>"


class UserProfile(Base):
    __tablename__ = "user_profiles"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id         = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    avatar_url      = Column(String(500), nullable=True)
    native_language = Column(String(50), nullable=True)   
    bio             = Column(Text, nullable=True)
    preferred_voice = Column(String(50), default="female") 
    daily_goal_mins = Column(Integer, default=15)          

    user = relationship("User", back_populates="profile")