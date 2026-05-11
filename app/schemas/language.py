from typing import Optional
from app.schemas.base import BaseSchema, TimestampSchema


class LanguageOut(TimestampSchema):
    name:         str
    code:         str
    native_name:  Optional[str] = None
    flag_emoji:   Optional[str] = None
    is_available: bool
    description:  Optional[str] = None


class LanguageCreate(BaseSchema):
    name:        str
    code:        str
    native_name: Optional[str] = None
    flag_emoji:  Optional[str] = None
    description: Optional[str] = None


class LanguageContentOut(TimestampSchema):
    language_id:   str
    source_url:    Optional[str] = None
    source_type:   Optional[str] = None
    title:         Optional[str] = None
    content:       str
    quality_score: float = 0.0