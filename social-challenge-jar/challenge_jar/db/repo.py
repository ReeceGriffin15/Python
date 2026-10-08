"""Storage boundary: maps rows to domain objects. Every query is user-scoped."""

from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..domain.models import Category, Challenge, Completion, Freeze, Log
from .tables import ChallengeRow, EarnedTitleRow, FreezeRow, LogRow, UserRow


def to_challenge(row: ChallengeRow) -> Challenge:
    return Challenge(
        id=row.id,
        slug=row.slug,
        tier=row.tier,
        suds_target=row.suds_target,
        text=row.text,
        safety_trap_to_drop=row.safety_trap_to_drop,
        success_criterion=row.success_criterion,
        category=Category(row.category),
        active=row.active,
    )


def to_log(row: LogRow) -> Log:
    return Log(
        id=row.id,
        date=row.date,
        challenge_id=row.challenge_id,
        tier=row.tier,
        plan_when=row.plan_when,
        plan_where=row.plan_where,
        predicted_suds=row.predicted_suds,
        feared_outcome=row.feared_outcome,
        actual_suds=row.actual_suds,
        what_happened=row.what_happened,
        completion=Completion(row.completion) if row.completion else None,
        safety_dropped=row.safety_dropped,
        logged_at=row.logged_at,
    )


class Repo:
    def __init__(self, session: Session, user_id: int):
        self.s = session
        self.user_id = user_id

    # -- user
    def user(self) -> UserRow:
        row = self.s.get(UserRow, self.user_id)
        if row is None:
            raise LookupError(f"user {self.user_id} not found")
        return row

    def set_current_tier(self, tier: int) -> None:
        self.user().current_tier = tier

    # -- challenges (shared catalogue, not user-scoped)
    def challenges(self) -> list[Challenge]:
        return [to_challenge(r) for r in self.s.scalars(select(ChallengeRow).order_by(ChallengeRow.tier, ChallengeRow.id))]

    # -- logs
    def logs(self) -> list[Log]:
        q = select(LogRow).where(LogRow.user_id == self.user_id).order_by(LogRow.date)
        return [to_log(r) for r in self.s.scalars(q)]

    def log_row(self, log_id: int) -> LogRow | None:
        row = self.s.get(LogRow, log_id)
        return row if row is not None and row.user_id == self.user_id else None

    def log_on(self, day: date) -> LogRow | None:
        q = select(LogRow).where(LogRow.user_id == self.user_id, LogRow.date == day)
        return self.s.scalars(q).first()

    def add_log(self, **fields) -> LogRow:
        row = LogRow(user_id=self.user_id, **fields)
        self.s.add(row)
        self.s.flush()
        return row

    def delete_log(self, row: LogRow) -> None:
        self.s.delete(row)

    # -- freezes
    def freezes(self) -> list[Freeze]:
        q = select(FreezeRow).where(FreezeRow.user_id == self.user_id).order_by(FreezeRow.date)
        return [Freeze(date=r.date) for r in self.s.scalars(q)]

    def add_freeze(self, day: date) -> None:
        self.s.add(FreezeRow(user_id=self.user_id, date=day))

    # -- titles
    def earned_titles(self) -> dict[str, datetime]:
        q = select(EarnedTitleRow).where(EarnedTitleRow.user_id == self.user_id)
        return {r.title_key: r.earned_at for r in self.s.scalars(q)}

    def add_titles(self, keys: list[str]) -> None:
        now = datetime.now(timezone.utc)
        for key in keys:
            self.s.add(EarnedTitleRow(user_id=self.user_id, title_key=key, earned_at=now))

    def flush(self) -> None:
        self.s.flush()

    def commit(self) -> None:
        self.s.commit()
