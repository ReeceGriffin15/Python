from __future__ import annotations

import dataclasses
from datetime import date, datetime, time

import pytest
from fastapi.testclient import TestClient

from challenge_jar.api.app import create_app
from challenge_jar.config import Rules, load_settings
from challenge_jar.domain.models import Category, Challenge, Completion, Log


class Clock:
    """Mutable "today" for driving the app through days."""

    def __init__(self, day: date):
        self.day = day

    def __call__(self, tz):
        return datetime.combine(self.day, time(9, 0), tzinfo=tz)


@pytest.fixture
def rules() -> Rules:
    return Rules()


@pytest.fixture
def clock() -> Clock:
    return Clock(date(2026, 10, 5))  # a Monday


@pytest.fixture
def client(tmp_path, clock):
    settings = dataclasses.replace(load_settings(), database_url=f"sqlite:///{tmp_path / 'test.db'}")
    with TestClient(create_app(settings, clock=clock)) as c:
        yield c


def make_log(i: int, day: date, tier: int = 1, completion: Completion | None = Completion.FULL,
             challenge_id: int = 1, predicted: int | None = 50, actual: int | None = 30,
             safety_dropped: bool | None = True) -> Log:
    return Log(id=i, date=day, challenge_id=challenge_id, tier=tier, plan_when="9am", plan_where="cafe",
               predicted_suds=predicted, actual_suds=actual, completion=completion,
               safety_dropped=safety_dropped)


def make_challenge(i: int, tier: int, category: Category) -> Challenge:
    return Challenge(id=i, slug=f"c{i}", tier=tier, suds_target=20, text=f"do {i}",
                     safety_trap_to_drop="phone", success_criterion="one sentence", category=category)
