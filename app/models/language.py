import uuid
from sqlalchemy import Column, String, Boolean, Text, ForeignKey, Float
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


class Language(Base):
    __tablename__ = "languages"

    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name         = Column(String(100), unique=True, nullable=False)  
    code         = Column(String(10),  unique=True, nullable=False)  
    native_name  = Column(String(100), nullable=True)                
    flag_emoji   = Column(String(10),  nullable=True)                
    is_available = Column(Boolean, default=False)  
    description  = Column(Text, nullable=True)

    content = relationship("LanguageContent", back_populates="language", cascade="all, delete-orphan")
    progress = relationship("UserProgress", back_populates="language")

    def __repr__(self):
        return f"<Language {self.name} ({self.code})>"


class LanguageContent(Base):
    __tablename__ = "language_contents"

    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    language_id  = Column(UUID(as_uuid=True), ForeignKey("languages.id", ondelete="CASCADE"), nullable=False)
    source_url   = Column(String(1000), nullable=True)   
    source_type  = Column(String(50),   nullable=True)   
    title        = Column(String(500),  nullable=True)
    content      = Column(Text,         nullable=False)  
    embedding_id = Column(String(255),  nullable=True)   
    quality_score = Column(Float,       default=0.0)     

    language = relationship("Language", back_populates="content")