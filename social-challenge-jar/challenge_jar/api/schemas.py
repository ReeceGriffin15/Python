from __future__ import annotations

import datetime as dt
from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints

from ..domain.models import Completion

Suds = Annotated[int, Field(ge=0, le=100)]
Line = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
Note = Annotated[str, StringConstraints(strip_whitespace=True, max_length=500)]


class PickIn(BaseModel):
    challenge_id: int
    plan_when: Line            # the "if" half of the if-then plan: when
    plan_where: Line           # ...and where
    predicted_suds: Suds | None = None
    feared_outcome: Note | None = None


class OutcomeIn(BaseModel):
    completion: Completion
    actual_suds: Suds | None = None
    what_happened: Note | None = None
    safety_dropped: bool | None = None
    predicted_suds: Suds | None = None  # only used if not given in the morning


class FreezeIn(BaseModel):
    date: dt.date | None = None


class TierIn(BaseModel):
    tier: int = Field(ge=1, le=4)
