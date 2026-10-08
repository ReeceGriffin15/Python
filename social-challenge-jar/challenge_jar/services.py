"""Application layer: the core loop as use-cases (today, pick, log, freeze...).

Takes a repo + rules + "today" and returns plain, JSON-ready dicts. The web API
is a thin adapter over this; a mobile client or CLI could use it unchanged.
Messages are stable codes, never prose - the UI owns the copy.
"""

from __future__ import annotations

from dataclasses import asdict
from datetime import date, datetime, timedelta, timezone

from .config import Rules
from .db.repo import Repo, to_log
from .db.tables import LogRow
from .domain import rules as R
from .domain.models import Challenge, Completion, Log
from .domain.titles import TITLE_KEYS, TitleContext, earned_titles

LOG_WINDOW_DAYS = 2  # how far back an unlogged plan can still be logged


class ServiceError(Exception):
    def __init__(self, code: str, status: int = 400):
        super().__init__(code)
        self.code = code
        self.status = status


def challenge_dict(c: Challenge) -> dict:
    return {
        "id": c.id,
        "slug": c.slug,
        "tier": c.tier,
        "suds_target": c.suds_target,
        "text": c.text,
        "safety_trap_to_drop": c.safety_trap_to_drop,
        "success_criterion": c.success_criterion,
        "category": c.category.value,
    }


def log_dict(log: Log, challenge: Challenge | None) -> dict:
    return {
        "id": log.id,
        "date": log.date.isoformat(),
        "tier": log.tier,
        "plan_when": log.plan_when,
        "plan_where": log.plan_where,
        "predicted_suds": log.predicted_suds,
        "feared_outcome": log.feared_outcome,
        "actual_suds": log.actual_suds,
        "what_happened": log.what_happened,
        "completion": log.completion.value if log.completion else None,
        "safety_dropped": log.safety_dropped,
        "prediction_gap": log.prediction_gap,
        "is_logged": log.is_logged,
        "challenge": challenge_dict(challenge) if challenge else None,
    }


class JarService:
    def __init__(self, repo: Repo, rules: Rules, today: date):
        self.repo = repo
        self.rules = rules
        self.today = today
        self._challenges: dict[int, Challenge] | None = None

    # ------------------------------------------------------------ helpers

    @property
    def challenges(self) -> dict[int, Challenge]:
        if self._challenges is None:
            self._challenges = {c.id: c for c in self.repo.challenges()}
        return self._challenges

    def _seed(self) -> str:
        return f"user-{self.repo.user_id}"

    def _progress(self, logs: list[Log]) -> R.TierProgress:
        return R.tier_progress(logs, self.repo.user().current_tier, self.rules)

    def _options(self, logs: list[Log], tier: int) -> list[Challenge]:
        return R.daily_options(list(self.challenges.values()), tier, logs, self.today, self._seed(), self.rules)

    def _log(self, log: Log | None) -> dict | None:
        return log_dict(log, self.challenges.get(log.challenge_id)) if log else None

    def _sync_titles(self, logs: list[Log]) -> list[str]:
        ctx = TitleContext(logs=logs, challenges=self.challenges, freezes=self.repo.freezes(), rules=self.rules)
        new = sorted(earned_titles(ctx) - set(self.repo.earned_titles()), key=TITLE_KEYS.index)
        self.repo.add_titles(new)
        return new

    # ------------------------------------------------------------ queries

    def today_state(self) -> dict:
        logs = self.repo.logs()
        freezes = self.repo.freezes()
        prog = self._progress(logs)
        entry = next((log for log in logs if log.date == self.today), None)
        pending = [
            log
            for log in logs
            if not log.is_logged and self.today - timedelta(days=LOG_WINDOW_DAYS) <= log.date < self.today
        ]
        week = R.weekly_summaries(logs, freezes, self.today, 1)[0]
        return {
            "date": self.today.isoformat(),
            "tier": asdict(prog),
            "entry": self._log(entry),
            "pending": [self._log(p) for p in pending],
            "options": [] if entry else [challenge_dict(c) for c in self._options(logs, prog.current)],
            "easier_tier": R.easier_tier(prog.current),
            "week": {
                "start": week.week_start.isoformat(),
                "score": week.score,
                "approaches": week.approaches,
                "freezes": week.freezes,
                "target": self.rules.week_target,
            },
            "freezes_left": R.freezes_left(freezes, self.today, self.rules),
            "frozen_today": any(f.date == self.today for f in freezes),
            "days_since_last": R.miss_run_before(self.today, logs, freezes),
        }

    def options(self, easier: bool = False) -> list[dict]:
        logs = self.repo.logs()
        tier = self._progress(logs).current
        if easier:
            tier = R.easier_tier(tier) or tier
        return [challenge_dict(c) for c in self._options(logs, tier)]

    def progress(self, weeks: int = 8) -> dict:
        logs = self.repo.logs()
        freezes = self.repo.freezes()
        logged = [log for log in logs if log.is_logged]
        approaches = [log for log in logged if log.is_approach]
        full = [log for log in approaches if log.is_full]
        return {
            "weeks": [
                {**asdict(w), "week_start": w.week_start.isoformat()}
                for w in R.weekly_summaries(logs, freezes, self.today, weeks)
            ],
            "week_target": self.rules.week_target,
            "totals": {
                "logged": len(logged),
                "approaches": len(approaches),
                "full": len(full),
                "pct_full": round(100 * len(full) / len(logged)) if logged else None,
                "safety_dropped": sum(1 for log in approaches if log.safety_dropped),
                "comebacks": len(R.comeback_days(logs, freezes, self.rules)),
            },
            "gap_by_tier": R.mean_gap_by_tier(logs),
            "tier": asdict(self._progress(logs)),
        }

    def history(self, limit: int = 30) -> list[dict]:
        logs = sorted(self.repo.logs(), key=lambda log: log.date, reverse=True)[:limit]
        return [self._log(log) for log in logs]

    def titles(self) -> list[dict]:
        earned = self.repo.earned_titles()
        return [
            {"key": k, "earned_at": earned[k].isoformat() if k in earned else None}
            for k in TITLE_KEYS
        ]

    def catalogue(self) -> dict:
        unlocked = R.unlocked_tier(self.repo.logs(), self.rules)
        return {
            "unlocked": unlocked,
            "challenges": [
                {**challenge_dict(c), "locked": c.tier > unlocked}
                for c in self.challenges.values()
                if c.active
            ],
        }

    # ------------------------------------------------------------ commands

    def pick(
        self,
        challenge_id: int,
        plan_when: str,
        plan_where: str,
        predicted_suds: int | None = None,
        feared_outcome: str | None = None,
    ) -> dict:
        if self.repo.log_on(self.today) is not None:
            raise ServiceError("already_picked", 409)
        offered = {c["id"] for c in self.options()} | {c["id"] for c in self.options(easier=True)}
        if challenge_id not in offered:
            raise ServiceError("not_offered")
        challenge = self.challenges[challenge_id]
        row = self.repo.add_log(
            date=self.today,
            challenge_id=challenge.id,
            tier=challenge.tier,
            plan_when=plan_when.strip(),
            plan_where=plan_where.strip(),
            predicted_suds=predicted_suds,
            feared_outcome=(feared_outcome or "").strip() or None,
        )
        self.repo.commit()
        return self._log(to_log(row))

    def unpick(self, log_id: int) -> None:
        row = self._own_row(log_id)
        if row.completion is not None or row.date != self.today:
            raise ServiceError("cannot_unpick")
        self.repo.delete_log(row)
        self.repo.commit()

    def log_outcome(
        self,
        log_id: int,
        completion: Completion,
        actual_suds: int | None = None,
        what_happened: str | None = None,
        safety_dropped: bool | None = None,
        predicted_suds: int | None = None,
    ) -> dict:
        row = self._own_row(log_id)
        if not self.today - timedelta(days=LOG_WINDOW_DAYS) <= row.date <= self.today:
            raise ServiceError("outside_log_window")
        approached = completion is not Completion.NONE
        if approached and actual_suds is None:
            raise ServiceError("actual_suds_required")

        logs_before = self.repo.logs()
        freezes = self.repo.freezes()
        was_approach = to_log(row).is_approach
        unlocked_before = R.unlocked_tier(logs_before, self.rules)

        if predicted_suds is not None and row.predicted_suds is None:
            row.predicted_suds = predicted_suds
        row.completion = completion.value
        row.actual_suds = actual_suds if approached else None
        row.safety_dropped = safety_dropped if approached else None
        row.what_happened = (what_happened or "").strip() or None
        row.logged_at = datetime.now(timezone.utc)
        self.repo.flush()

        logs = self.repo.logs()
        events: list[dict] = []
        if approached and not was_approach:
            if R.miss_run_before(row.date, logs, freezes) >= self.rules.comeback_gap_days:
                events.append({"type": "comeback"})
        unlocked_after = R.unlocked_tier(logs, self.rules)
        if unlocked_after > unlocked_before:
            self.repo.set_current_tier(unlocked_after)
            events.append({"type": "tier_unlocked", "tier": unlocked_after})
        events += [{"type": "title", "key": k} for k in self._sync_titles(logs)]
        self.repo.commit()

        return {
            "entry": self._log(to_log(row)),
            "events": events,
            "tier": asdict(self._progress(logs)),
        }

    def use_freeze(self, day: date | None = None) -> dict:
        day = day or self.today
        try:
            R.check_freeze(day, self.today, self.repo.logs(), self.repo.freezes(), self.rules)
        except R.FreezeError as e:
            raise ServiceError(f"freeze_{e.code}") from e
        self.repo.add_freeze(day)
        self.repo.commit()
        return {"date": day.isoformat(), "freezes_left": R.freezes_left(self.repo.freezes(), day, self.rules)}

    def set_tier(self, tier: int) -> dict:
        logs = self.repo.logs()
        if not 1 <= tier <= R.unlocked_tier(logs, self.rules):
            raise ServiceError("tier_locked")
        self.repo.set_current_tier(tier)
        self.repo.commit()
        return asdict(self._progress(logs))

    def _own_row(self, log_id: int) -> LogRow:
        row = self.repo.log_row(log_id)
        if row is None:
            raise ServiceError("not_found", 404)
        return row
