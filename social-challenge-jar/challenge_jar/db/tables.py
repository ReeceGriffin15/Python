"""SQLAlchemy tables. Every per-person row carries ``user_id`` from day one so
adding real accounts later is an auth change, not a migration of the core loop."""

from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class UserRow(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    display_name: Mapped[str] = mapped_column(String(80), default="Me")
    timezone: Mapped[str] = mapped_column(String(64), default="Europe/London")
    current_tier: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class ChallengeRow(Base):
    __tablename__ = "challenges"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(80), unique=True)
    tier: Mapped[int] = mapped_column(Integer, index=True)
    suds_target: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)
    safety_trap_to_drop: Mapped[str] = mapped_column(Text)
    success_criterion: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(32), index=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class LogRow(Base):
    __tablename__ = "logs"
    __table_args__ = (UniqueConstraint("user_id", "date", name="uq_logs_user_date"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    date: Mapped[date] = mapped_column(Date)
    challenge_id: Mapped[int] = mapped_column(ForeignKey("challenges.id"))
    tier: Mapped[int] = mapped_column(Integer)
    # morning: if-then plan + prediction
    plan_when: Mapped[str] = mapped_column(String(200))
    plan_where: Mapped[str] = mapped_column(String(200))
    predicted_suds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    feared_outcome: Mapped[str | None] = mapped_column(Text, nullable=True)
    # evening: outcome
    actual_suds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    what_happened: Mapped[str | None] = mapped_column(Text, nullable=True)
    completion: Mapped[str | None] = mapped_column(String(16), nullable=True)  # none | partial | full
    safety_dropped: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    logged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class FreezeRow(Base):
    __tablename__ = "freezes"
    __table_args__ = (UniqueConstraint("user_id", "date", name="uq_freezes_user_date"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    date: Mapped[date] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class EarnedTitleRow(Base):
    __tablename__ = "earned_titles"
    __table_args__ = (UniqueConstraint("user_id", "title_key", name="uq_titles_user_key"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    title_key: Mapped[str] = mapped_column(String(64))
    earned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
