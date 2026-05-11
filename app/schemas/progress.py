from typing import Optional, List
from uuid import UUID

from app.schemas.base import BaseSchema, TimestampSchema


class ProgressCreate(BaseSchema):
    user_id:            UUID
    language_id:        UUID
    total_xp:           int = 0
    streak_days:        int = 0
    longest_streak:     int = 0
    total_sessions:     int = 0
    total_time_mins:    int = 0
    words_learned:      int = 0
    avg_pronunciation:  float = 0.0


class ProgressUpdate(BaseSchema):
    total_xp:           Optional[int] = None
    streak_days:        Optional[int] = None
    longest_streak:     Optional[int] = None
    total_sessions:     Optional[int] = None
    total_time_mins:    Optional[int] = None
    words_learned:      Optional[int] = None
    avg_pronunciation:  Optional[float] = None


class AchievementOut(TimestampSchema):
    
    progress_id:  UUID
    title:        str
    description:  Optional[str]  = None
    icon:         Optional[str]  = None
    xp_reward:    int            = 0
    is_unlocked:  bool           = False


class ProgressOut(TimestampSchema):
   
    user_id:            UUID
    language_id:        UUID
    total_xp:           int    = 0
    streak_days:        int    = 0
    longest_streak:     int    = 0
    total_sessions:     int    = 0
    total_time_mins:    int    = 0
    words_learned:      int    = 0
    avg_pronunciation:  float  = 0.0
    achievements:       List[AchievementOut] = []


class ProgressSummary(BaseSchema):
   
    language_id:     UUID
    language_name:   Optional[str] = None
    language_flag:   Optional[str] = None
    total_xp:        int  = 0
    streak_days:     int  = 0
    total_sessions:  int  = 0