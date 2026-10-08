"""Plain domain objects. No database or web imports here."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum


class Category(str, Enum):
    STRANGER = "stranger"          # stranger micro-contact
    SERVICE = "service"            # service staff
    PEER = "peer"                  # peer small-talk
    WORK_VOICE = "work_voice"      # work / meeting voice
    DISAGREEMENT = "disagreement"
    HOSTING = "hosting"
    PHONE_VOICE = "phone_voice"
    NETWORKING = "networking"      # networking (property / bp)


class Completion(str, Enum):
    NONE = "none"
    PARTIAL = "partial"
    FULL = "full"


# Nominal SUDs band per tier (0-100 scale).
TIER_SUDS = {1: (10, 25), 2: (25, 40), 3: (40, 60), 4: (60, 80)}


@dataclass(frozen=True)
class Challenge:
    id: int
    slug: str
    tier: int
    suds_target: int
    text: str
    safety_trap_to_drop: str
    success_criterion: str
    category: Category
    active: bool = True


@dataclass(frozen=True)
class Log:
    """One day's entry: the morning plan plus (later) the evening outcome.

    ``tier`` is snapshotted at pick time so editing a challenge later never
    rewrites unlock history.
    """

    id: int
    date: date
    challenge_id: int
    tier: int
    plan_when: str
    plan_where: str
    predicted_suds: int | None = None
    feared_outcome: str | None = None
    actual_suds: int | None = None
    what_happened: str | None = None
    completion: Completion | None = None
    safety_dropped: bool | None = None
    logged_at: datetime | None = None

    @property
    def is_logged(self) -> bool:
        return self.completion is not None

    @property
    def is_approach(self) -> bool:
        return self.completion in (Completion.PARTIAL, Completion.FULL)

    @property
    def is_full(self) -> bool:
        return self.completion is Completion.FULL

    @property
    def prediction_gap(self) -> int | None:
        """Expected minus actual distress. Positive = it was easier than feared."""
        if self.predicted_suds is None or self.actual_suds is None or not self.is_approach:
            return None
        return self.predicted_suds - self.actual_suds


@dataclass(frozen=True)
class Freeze:
    date: date
