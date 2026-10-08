"""Titles: milestone unlocks for showing up, never for perfection.

Rules return stable keys; display names and hints live in the UI copy file.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass

from ..config import Rules
from .models import Category, Challenge, Freeze, Log
from .rules import comeback_days


@dataclass(frozen=True)
class TitleContext:
    logs: Sequence[Log]
    challenges: Mapping[int, Challenge]
    freezes: Sequence[Freeze]
    rules: Rules

    def approaches(self) -> list[Log]:
        return [log for log in self.logs if log.is_approach]

    def full_in(self, category: Category, min_tier: int = 1) -> int:
        return sum(
            1
            for log in self.logs
            if log.is_full
            and log.tier >= min_tier
            and (c := self.challenges.get(log.challenge_id)) is not None
            and c.category is category
        )


@dataclass(frozen=True)
class TitleRule:
    key: str
    earned: Callable[[TitleContext], bool]


TITLE_RULES: tuple[TitleRule, ...] = (
    TitleRule("rookie_nod", lambda c: len(c.approaches()) >= 1),
    TitleRule("brief_eye_contact", lambda c: len(c.approaches()) >= 5),
    TitleRule("one_sentence_out", lambda c: len(c.approaches()) >= 10),
    TitleRule("barista_banter", lambda c: c.full_in(Category.SERVICE) >= 3),
    TitleRule("meeting_voice", lambda c: c.full_in(Category.WORK_VOICE) >= 3),
    TitleRule(
        "cold_open",
        lambda c: c.full_in(Category.STRANGER, min_tier=3) + c.full_in(Category.NETWORKING, min_tier=3) >= 1,
    ),
    TitleRule("held_disagreement", lambda c: c.full_in(Category.DISAGREEMENT, min_tier=2) >= 1),
    TitleRule("hosted_the_table", lambda c: c.full_in(Category.HOSTING, min_tier=3) >= 1),
    TitleRule("safety_dropper", lambda c: sum(1 for log in c.approaches() if log.safety_dropped) >= 10),
    TitleRule("comeback_kid", lambda c: len(comeback_days(c.logs, c.freezes, c.rules)) >= 1),
)

TITLE_KEYS: tuple[str, ...] = tuple(r.key for r in TITLE_RULES)


def earned_titles(ctx: TitleContext) -> set[str]:
    return {r.key for r in TITLE_RULES if r.earned(ctx)}
