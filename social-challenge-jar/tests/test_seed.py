from collections import Counter

from challenge_jar.domain.models import Category
from challenge_jar.seed.loader import load_seed


def test_seed_size_and_spread():
    items = load_seed()  # also validates slugs, categories and SUDs bands
    assert 40 <= len(items) <= 60
    per_tier = Counter(i["tier"] for i in items)
    assert set(per_tier) == {1, 2, 3, 4}
    assert min(per_tier.values()) >= 10
    for tier in (1, 2, 3, 4):
        cats = {i["category"] for i in items if i["tier"] == tier}
        assert len(cats) >= 6, f"tier {tier} only covers {cats}"
    assert {i["category"] for i in items} == {c.value for c in Category}


def test_every_card_is_complete():
    for i in load_seed():
        for field in ("text", "drop", "success"):
            assert i[field].strip(), f"{i['slug']} missing {field}"
