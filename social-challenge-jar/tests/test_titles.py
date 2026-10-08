from datetime import date, timedelta

from challenge_jar.domain.models import Category, Completion
from challenge_jar.domain.titles import TITLE_KEYS, TitleContext, earned_titles

from .conftest import make_challenge, make_log

MON = date(2026, 10, 5)


def ctx(logs, challenges, freezes=(), rules=None):
    from challenge_jar.config import Rules
    return TitleContext(logs=logs, challenges={c.id: c for c in challenges}, freezes=list(freezes), rules=rules or Rules())


def test_ten_titles_defined():
    assert len(TITLE_KEYS) == 10


def test_nothing_for_nothing():
    assert earned_titles(ctx([], [])) == set()
    missed = [make_log(1, MON, completion=Completion.NONE)]
    assert earned_titles(ctx(missed, [make_challenge(1, 1, Category.STRANGER)])) == set()


def test_partial_counts_as_approach():
    logs = [make_log(1, MON, completion=Completion.PARTIAL, safety_dropped=False)]
    assert earned_titles(ctx(logs, [make_challenge(1, 1, Category.STRANGER)])) == {"rookie_nod"}


def test_category_titles():
    cs = [make_challenge(1, 1, Category.SERVICE), make_challenge(2, 3, Category.HOSTING),
          make_challenge(3, 2, Category.DISAGREEMENT), make_challenge(4, 3, Category.STRANGER)]
    logs = [make_log(i, MON + timedelta(days=i), challenge_id=1, safety_dropped=False) for i in range(3)]
    logs += [make_log(10, MON + timedelta(days=4), tier=3, challenge_id=2, safety_dropped=False),
             make_log(11, MON + timedelta(days=5), tier=2, challenge_id=3, safety_dropped=False),
             make_log(12, MON + timedelta(days=6), tier=3, challenge_id=4, safety_dropped=False)]
    got = earned_titles(ctx(logs, cs))
    assert {"rookie_nod", "brief_eye_contact", "barista_banter", "hosted_the_table",
            "held_disagreement", "cold_open"} <= got
    assert "one_sentence_out" not in got and "safety_dropper" not in got


def test_safety_dropper_and_comeback():
    cs = [make_challenge(1, 1, Category.STRANGER)]
    logs = [make_log(i, MON + timedelta(days=i)) for i in range(10)]
    assert "safety_dropper" in earned_titles(ctx(logs, cs))
    assert "comeback_kid" not in earned_titles(ctx(logs, cs))
    logs.append(make_log(99, MON + timedelta(days=20)))
    assert "comeback_kid" in earned_titles(ctx(logs, cs))
