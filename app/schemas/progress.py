from typing import Optional, List
from uuid import UUID

from app.schemas.base import BaseSchema, TimestampSchema


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