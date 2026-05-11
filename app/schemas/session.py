from typing import Optional
from uuid import UUID
from datetime import datetime

from app.schemas.base import BaseSchema, TimestampSchema
from app.models.session import SessionMode


class SessionCreate(BaseSchema):
    language_id: UUID
    mode:        SessionMode


class SessionEnd(BaseSchema):
    duration_s: int   
    xp_earned:  int = 0


class SessionOut(TimestampSchema):
    user_id:     UUID
    language_id: UUID
    mode:        SessionMode
    started_at:  Optional[datetime] = None
    ended_at:    Optional[datetime] = None
    duration_s:  int  = 0
    xp_earned:   int  = 0