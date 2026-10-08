"""Idempotent seeding. Challenges are upserted by slug, so editing the JSON and
restarting updates the catalogue without touching anyone's history."""

from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..domain.models import TIER_SUDS, Category
from ..db.tables import ChallengeRow, UserRow

SEED_FILE = Path(__file__).with_name("challenges.json")


def load_seed(path: Path = SEED_FILE) -> list[dict]:
    items = json.loads(path.read_text(encoding="utf-8"))
    slugs = set()
    for item in items:
        if item["slug"] in slugs:
            raise ValueError(f"duplicate slug {item['slug']}")
        slugs.add(item["slug"])
        Category(item["category"])  # validates
        lo, hi = TIER_SUDS[item["tier"]]
        if not lo <= item["suds"] <= hi:
            raise ValueError(f"{item['slug']}: suds {item['suds']} outside tier {item['tier']} band {lo}-{hi}")
    return items


def seed_challenges(session: Session, path: Path = SEED_FILE) -> int:
    items = load_seed(path)
    existing = {r.slug: r for r in session.scalars(select(ChallengeRow))}
    for item in items:
        row = existing.pop(item["slug"], None) or ChallengeRow(slug=item["slug"])
        row.tier = item["tier"]
        row.suds_target = item["suds"]
        row.text = item["text"]
        row.safety_trap_to_drop = item["drop"]
        row.success_criterion = item["success"]
        row.category = item["category"]
        row.active = item.get("active", True)
        session.add(row)
    for row in existing.values():  # removed from the seed: retire, never delete (logs point at it)
        row.active = False
    session.commit()
    return len(items)


def ensure_default_user(session: Session, timezone: str) -> int:
    """Single-user mode: user 1 always exists. Real auth replaces this later."""
    user = session.get(UserRow, 1)
    if user is None:
        session.add(UserRow(id=1, display_name="Me", timezone=timezone, current_tier=1))
        session.commit()
    return 1
