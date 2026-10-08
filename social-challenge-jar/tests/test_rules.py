from datetime import date, timedelta

from challenge_jar.config import Rules
from challenge_jar.domain import rules as R
from challenge_jar.domain.models import Category, Completion, Freeze

from .conftest import make_challenge, make_log

MON = date(2026, 10, 5)


def test_prediction_gap_only_for_approaches():
    assert make_log(1, MON, predicted=60, actual=35).prediction_gap == 25
    assert make_log(1, MON, completion=Completion.NONE).prediction_gap is None
    assert make_log(1, MON, predicted=None).prediction_gap is None


def test_unlock_needs_n_full_completions_in_order(rules):
    four = [make_log(i, MON + timedelta(days=i), tier=1) for i in range(4)]
    assert R.unlocked_tier(four, rules) == 1
    partial = make_log(9, MON, tier=1, completion=Completion.PARTIAL)
    assert R.unlocked_tier([*four, partial], rules) == 1
    five = [*four, make_log(5, MON + timedelta(days=5), tier=1)]
    assert R.unlocked_tier(five, rules) == 2
    # tier-3 completions can't skip tier 2
    t3 = [make_log(10 + i, MON, tier=3) for i in range(10)]
    assert R.unlocked_tier([*five, *t3], rules) == 2


def test_unlock_threshold_is_configurable():
    logs = [make_log(i, MON, tier=1) for i in range(3)]
    assert R.unlocked_tier(logs, Rules(unlock_full_completions=3)) == 2


def test_tier_progress_clamps_current_to_unlocked(rules):
    prog = R.tier_progress([], current=4, rules=rules)
    assert prog.current == 1 and prog.unlocked == 1 and prog.needed == 5


def _catalogue():
    cats = list(Category)
    return [make_challenge(i, tier=1 + i % 4, category=cats[(i // 4) % len(cats)]) for i in range(1, 41)]


def test_daily_options_same_tier_distinct_and_stable(rules):
    cs = _catalogue()
    a = R.daily_options(cs, 2, [], MON, "u1", rules)
    b = R.daily_options(cs, 2, [], MON, "u1", rules)
    assert [c.id for c in a] == [c.id for c in b]
    assert len(a) == 3
    assert all(c.tier == 2 for c in a)
    assert len({c.category for c in a}) == 3
    # different day, different draw (very likely with 10 candidates)
    days = {tuple(c.id for c in R.daily_options(cs, 2, [], MON + timedelta(days=d), "u1", rules)) for d in range(7)}
    assert len(days) > 1


def test_daily_options_avoid_recent_full_completions(rules):
    cs = _catalogue()
    tier1 = [c for c in cs if c.tier == 1]
    recent = [make_log(i, MON - timedelta(days=1), challenge_id=c.id) for i, c in enumerate(tier1[:5])]
    picked = R.daily_options(cs, 1, recent, MON, "u1", rules)
    assert not {c.id for c in picked} & {c.id for c in tier1[:5]}


def test_daily_options_fall_back_when_pool_small(rules):
    cs = [make_challenge(i, 1, Category.STRANGER) for i in range(1, 4)]
    recent = [make_log(i, MON - timedelta(days=1), challenge_id=i) for i in range(1, 4)]
    assert len(R.daily_options(cs, 1, recent, MON, "u1", rules)) == 3


def test_inactive_challenges_never_offered(rules):
    from dataclasses import replace
    cs = [replace(c, active=False) if c.tier == 1 else c for c in _catalogue()]
    assert R.daily_options(cs, 1, [], MON, "u1", rules) == []


def test_week_summary_counts_approaches_and_freezes(rules):
    logs = [
        make_log(1, MON, predicted=60, actual=30),
        make_log(2, MON + timedelta(days=1), completion=Completion.PARTIAL, predicted=40, actual=30),
        make_log(3, MON + timedelta(days=2), completion=Completion.NONE),
        make_log(4, MON - timedelta(days=1)),  # previous week
    ]
    freezes = [Freeze(MON + timedelta(days=3))]
    weeks = R.weekly_summaries(logs, freezes, MON + timedelta(days=4), weeks=2)
    prev, this = weeks
    assert prev.week_start == MON - timedelta(days=7) and prev.approaches == 1
    assert this.approaches == 2 and this.full == 1 and this.freezes == 1 and this.score == 3
    assert this.mean_gap == 20.0


def test_freeze_rules(rules):
    today = MON + timedelta(days=2)
    R.check_freeze(MON, today, [], [], rules)
    for day, logs, freezes, code in [
        (today + timedelta(days=1), [], [], "future"),
        (MON - timedelta(days=1), [], [], "outside_week"),
        (MON, [], [Freeze(MON)], "already_frozen"),
        (MON, [make_log(1, MON)], [], "day_has_approach"),
        (MON, [], [Freeze(date(2026, 10, 1)), Freeze(date(2026, 10, 2))], "none_left"),
    ]:
        try:
            R.check_freeze(day, today, logs, freezes, rules)
        except R.FreezeError as e:
            assert e.code == code
        else:
            raise AssertionError(f"expected {code}")
    # a missed (logged "none") day can still be frozen
    R.check_freeze(MON, today, [make_log(1, MON, completion=Completion.NONE)], [], rules)


def test_freezes_reset_monthly(rules):
    used = [Freeze(date(2026, 9, 29)), Freeze(date(2026, 9, 30))]
    assert R.freezes_left(used, date(2026, 9, 30), rules) == 0
    assert R.freezes_left(used, date(2026, 10, 1), rules) == 2


def test_miss_run_and_comebacks(rules):
    logs = [make_log(1, MON), make_log(2, MON + timedelta(days=5))]
    assert R.miss_run_before(MON, logs, []) == 0  # first ever day is a start, not a comeback
    assert R.miss_run_before(MON + timedelta(days=5), logs, []) == 4
    assert R.comeback_days(logs, [], rules) == [MON + timedelta(days=5)]
    # freezes cover days, so the gap shrinks below the threshold
    freezes = [Freeze(MON + timedelta(days=d)) for d in (2, 3)]
    assert R.miss_run_before(MON + timedelta(days=5), logs, freezes) == 1
    assert R.comeback_days(logs, freezes, rules) == []


def test_gap_by_tier_trend():
    logs = [make_log(i, MON + timedelta(days=i), predicted=60, actual=60 - g) for i, g in enumerate([40, 30, 10, 0])]
    out = R.mean_gap_by_tier(logs)[1]
    assert out == {"count": 4, "mean": 20.0, "early": 35.0, "recent": 5.0}
