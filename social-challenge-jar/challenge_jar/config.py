"""Runtime settings, read from environment variables.

Everything tunable about the core loop lives here so it can be changed without
touching domain code (and later, overridden per user).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _int(name: str, default: int) -> int:
    return int(os.environ.get(name, default))


@dataclass(frozen=True)
class Rules:
    """Knobs for the core loop. Defaults follow the brief."""

    unlock_full_completions: int = 5   # full completions at a tier to unlock the next
    options_per_day: int = 3           # same-tier cards offered each morning
    freezes_per_month: int = 2
    comeback_gap_days: int = 3         # missed days in a row before a return counts as a comeback
    week_target: int = 5               # approaches per week
    recent_repeat_days: int = 7        # avoid re-offering a challenge fully done this recently
    max_tier: int = 4


@dataclass(frozen=True)
class Settings:
    database_url: str
    timezone: str
    web_dir: Path
    rules: Rules


def load_settings() -> Settings:
    root = Path(__file__).resolve().parent.parent
    return Settings(
        database_url=os.environ.get("JAR_DATABASE_URL", f"sqlite:///{root / 'challenge_jar.db'}"),
        timezone=os.environ.get("JAR_TIMEZONE", "Europe/London"),
        web_dir=Path(os.environ.get("JAR_WEB_DIR", root / "web")),
        rules=Rules(
            unlock_full_completions=_int("JAR_UNLOCK_N", 5),
            options_per_day=_int("JAR_OPTIONS_PER_DAY", 3),
            freezes_per_month=_int("JAR_FREEZES_PER_MONTH", 2),
            comeback_gap_days=_int("JAR_COMEBACK_GAP_DAYS", 3),
            week_target=_int("JAR_WEEK_TARGET", 5),
        ),
    )
