"""Core-loop rules: tiers, daily options, week score, freezes, comebacks.

Every function is pure: give it history, get an answer. That keeps the rules
testable and reusable whatever the storage or UI looks like.
"""

from __future__ import annotations

import random
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from statistics import mean

from ..config import Rules
from .models import Challenge, Freeze, Log

# ---------------------------------------------------------------- tiers


def full_completions_at(logs: Iterable[Log], tier: int) -> int:
    return sum(1 for log in logs if log.is_full and log.tier == tier)


def unlocked_tier(logs: Sequence[Log], rules: Rules) -> int:
    """Highest tier unlocked. Tiers unlock strictly in order: N full completions
    at tier t opens tier t+1. No skipping."""
    tier = 1
    while tier < rules.max_tier and full_completions_at(logs, tier) >= rules.unlock_full_completions:
        tier += 1
    return tier


@dataclass(frozen=True)
class TierProgress:
    current: int
    unlocked: int
    full_at_current: int
    needed: int
    is_max: bool


def tier_progress(logs: Sequence[Log], current: int, rules: Rules) -> TierProgress:
    unlocked = unlocked_tier(logs, rules)
    current = max(1, min(current, unlocked))
    return TierProgress(
        current=current,
        unlocked=unlocked,
        full_at_current=full_completions_at(logs, current),
        needed=rules.unlock_full_completions,
        is_max=current >= rules.max_tier,
    )


# ---------------------------------------------------------------- daily options


def daily_options(
    challenges: Sequence[Challenge],
    tier: int,
    logs: Sequence[Log],
    day: date,
    seed: str,
    rules: Rules,
) -> list[Challenge]:
    """2-3 challenges at exactly ``tier`` for ``day``.

    Deterministic per (seed, day, tier) so reloading the page can't be used as a
    slot machine. Spreads across categories and avoids repeating something
    fully done in the last ``recent_repeat_days`` when there's enough choice.
    """
    pool = [c for c in challenges if c.active and c.tier == tier]
    recent_cutoff = day - timedelta(days=rules.recent_repeat_days)
    recent = {log.challenge_id for log in logs if log.is_full and recent_cutoff <= log.date < day}
    fresh = [c for c in pool if c.id not in recent]
    if len(fresh) >= rules.options_per_day:
        pool = fresh

    rng = random.Random(f"{seed}:{day.isoformat()}:{tier}")
    pool = sorted(pool, key=lambda c: c.id)
    rng.shuffle(pool)

    picked: list[Challenge] = []
    seen_categories = set()
    for c in pool:
        if c.category not in seen_categories:
            picked.append(c)
            seen_categories.add(c.category)
        if len(picked) == rules.options_per_day:
            return picked
    for c in pool:
        if c not in picked:
            picked.append(c)
        if len(picked) == rules.options_per_day:
            break
    return picked


def easier_tier(current: int) -> int | None:
    """The tier offered on a low-energy day, or None when already at tier 1."""
    return current - 1 if current > 1 else None


# ---------------------------------------------------------------- weeks & freezes


def week_start(d: date) -> date:
    return d - timedelta(days=d.weekday())


def month_key(d: date) -> tuple[int, int]:
    return (d.year, d.month)


def freezes_left(freezes: Iterable[Freeze], on: date, rules: Rules) -> int:
    used = sum(1 for f in freezes if month_key(f.date) == month_key(on))
    return max(0, rules.freezes_per_month - used)


class FreezeError(ValueError):
    """Raised with a stable ``code`` the UI maps to copy."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def check_freeze(day: date, today: date, logs: Sequence[Log], freezes: Sequence[Freeze], rules: Rules) -> None:
    """Freezes cover a missed day in the current week, up to today."""
    if day > today:
        raise FreezeError("future")
    if week_start(day) != week_start(today):
        raise FreezeError("outside_week")
    if any(f.date == day for f in freezes):
        raise FreezeError("already_frozen")
    if any(log.date == day and log.is_approach for log in logs):
        raise FreezeError("day_has_approach")
    if freezes_left(freezes, day, rules) <= 0:
        raise FreezeError("none_left")


@dataclass(frozen=True)
class WeekSummary:
    week_start: date
    approaches: int
    full: int
    freezes: int
    score: int               # approaches + freezes, toward the weekly target
    mean_gap: float | None   # mean(predicted - actual) over approaches with both ratings
    safety_dropped: int


def weekly_summaries(
    logs: Sequence[Log], freezes: Sequence[Freeze], today: date, weeks: int
) -> list[WeekSummary]:
    """Oldest first, ending with the current week."""
    this_week = week_start(today)
    out = []
    for i in range(weeks - 1, -1, -1):
        start = this_week - timedelta(weeks=i)
        end = start + timedelta(days=7)
        wk = [log for log in logs if start <= log.date < end]
        approaches = [log for log in wk if log.is_approach]
        gaps = [log.prediction_gap for log in approaches if log.prediction_gap is not None]
        n_freezes = sum(1 for f in freezes if start <= f.date < end)
        out.append(
            WeekSummary(
                week_start=start,
                approaches=len(approaches),
                full=sum(1 for log in approaches if log.is_full),
                freezes=n_freezes,
                score=len(approaches) + n_freezes,
                mean_gap=round(mean(gaps), 1) if gaps else None,
                safety_dropped=sum(1 for log in approaches if log.safety_dropped),
            )
        )
    return out


def mean_gap_by_tier(logs: Sequence[Log]) -> dict[int, dict[str, float | int | None]]:
    """Per tier: overall mean gap, plus first-half vs second-half means so a
    trend toward calibration is visible without a second chart."""
    out: dict[int, dict[str, float | int | None]] = {}
    for tier in sorted({log.tier for log in logs}):
        gaps = [
            log.prediction_gap
            for log in sorted(logs, key=lambda x: x.date)
            if log.tier == tier and log.prediction_gap is not None
        ]
        if not gaps:
            continue
        half = len(gaps) // 2
        out[tier] = {
            "count": len(gaps),
            "mean": round(mean(gaps), 1),
            "early": round(mean(gaps[:half]), 1) if half else None,
            "recent": round(mean(gaps[half:]), 1) if half else None,
        }
    return out


# ---------------------------------------------------------------- misses & comebacks


def _covered_days(logs: Iterable[Log], freezes: Iterable[Freeze]) -> set[date]:
    return {log.date for log in logs if log.is_approach} | {f.date for f in freezes}


def miss_run_before(day: date, logs: Sequence[Log], freezes: Sequence[Freeze]) -> int:
    """Consecutive uncovered days immediately before ``day``, counted back to
    the most recent approach or freeze. Zero if there's no earlier activity
    (the very first day is a start, not a comeback)."""
    covered = _covered_days(logs, freezes)
    earlier = [d for d in covered if d < day]
    if not earlier:
        return 0
    return (day - max(earlier)).days - 1


def comeback_days(logs: Sequence[Log], freezes: Sequence[Freeze], rules: Rules) -> list[date]:
    """Days where an approach followed a run of >= comeback_gap_days misses."""
    approach_days = sorted({log.date for log in logs if log.is_approach})
    return [d for d in approach_days if miss_run_before(d, logs, freezes) >= rules.comeback_gap_days]
