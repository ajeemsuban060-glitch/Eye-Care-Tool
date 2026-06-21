"""Data models representing rows in the database."""

from dataclasses import dataclass
from typing import Optional

@dataclass
class Session:
    id: Optional[int]
    started_at: str
    ended_at: Optional[str] = None

@dataclass
class Break:
    id: Optional[int]
    session_id: int
    triggered_at: str
    trigger_reason: str  # 'time' or 'fatigue'
    active_seconds_before_break: int
    fatigue_score: Optional[float] = None
    user_response: Optional[str] = None  # 'taken', 'skipped', 'snoozed'

# Helper functions to insert/update can be added here.