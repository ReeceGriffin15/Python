from datetime import timedelta


def pick_first(client, easier=False):
    opts = client.get("/api/options", params={"easier": easier}).json() if easier else client.get("/api/today").json()["options"]
    r = client.post("/api/plans", json={
        "challenge_id": opts[0]["id"], "plan_when": "after the 9am stand-up",
        "plan_where": "Hitchin station cafe", "predicted_suds": 50, "feared_outcome": "They look annoyed",
    })
    assert r.status_code == 201, r.text
    return r.json()


def log_full(client, log_id, actual=20, dropped=True):
    r = client.post(f"/api/logs/{log_id}/outcome", json={
        "completion": "full", "actual_suds": actual, "what_happened": "Fine, short chat", "safety_dropped": dropped,
    })
    assert r.status_code == 200, r.text
    return r.json()


def test_morning_shows_current_tier_options(client):
    t = client.get("/api/today").json()
    assert t["tier"] == {"current": 1, "unlocked": 1, "full_at_current": 0, "needed": 5, "is_max": False}
    assert 2 <= len(t["options"]) <= 3
    assert all(o["tier"] == 1 for o in t["options"])
    assert all(o["safety_trap_to_drop"] and o["success_criterion"] for o in t["options"])
    assert t["entry"] is None and t["freezes_left"] == 2 and t["easier_tier"] is None
    # reloading doesn't reshuffle
    assert client.get("/api/today").json()["options"] == t["options"]


def test_if_then_plan_is_required(client):
    opt = client.get("/api/today").json()["options"][0]
    r = client.post("/api/plans", json={"challenge_id": opt["id"], "plan_when": "  ", "plan_where": "office"})
    assert r.status_code == 422


def test_cannot_pick_unoffered_or_twice(client):
    catalogue = client.get("/api/challenges").json()["challenges"]
    t4 = next(c for c in catalogue if c["tier"] == 4)
    assert t4["locked"] is True
    r = client.post("/api/plans", json={"challenge_id": t4["id"], "plan_when": "x", "plan_where": "y"})
    assert r.status_code == 400 and r.json()["error"] == "not_offered"
    pick_first(client)
    opt = client.get("/api/options").json()[1]
    r = client.post("/api/plans", json={"challenge_id": opt["id"], "plan_when": "x", "plan_where": "y"})
    assert r.status_code == 409


def test_evening_log_reports_gap(client):
    entry = pick_first(client)
    out = log_full(client, entry["id"], actual=20)
    assert out["entry"]["prediction_gap"] == 30
    assert {"type": "title", "key": "rookie_nod"} in out["events"]
    t = client.get("/api/today").json()
    assert t["entry"]["is_logged"] and t["options"] == []
    assert t["week"]["score"] == 1


def test_none_completion_needs_no_rating_and_scores_nothing(client):
    entry = pick_first(client)
    r = client.post(f"/api/logs/{entry['id']}/outcome", json={"completion": "none", "what_happened": "Bottled it"})
    assert r.status_code == 200
    assert r.json()["events"] == []
    assert client.get("/api/today").json()["week"]["score"] == 0


def test_approach_requires_actual_suds(client):
    entry = pick_first(client)
    r = client.post(f"/api/logs/{entry['id']}/outcome", json={"completion": "partial"})
    assert r.json()["error"] == "actual_suds_required"


def test_unpick_before_logging(client):
    entry = pick_first(client)
    assert client.delete(f"/api/plans/{entry['id']}").status_code == 204
    assert client.get("/api/today").json()["entry"] is None


def test_five_full_completions_unlock_tier_two(client, clock):
    for i in range(5):
        out = log_full(client, pick_first(client)["id"])
        clock.day += timedelta(days=1)
    assert {"type": "tier_unlocked", "tier": 2} in out["events"]
    t = client.get("/api/today").json()
    assert t["tier"]["current"] == 2 and t["tier"]["unlocked"] == 2
    assert all(o["tier"] == 2 for o in t["options"])
    assert t["easier_tier"] == 1
    assert all(o["tier"] == 1 for o in client.get("/api/options", params={"easier": True}).json())
    # a low-energy pick from the easier tier is allowed
    assert pick_first(client, easier=True)["tier"] == 1
    # step down by choice, but never up past unlocked
    assert client.put("/api/me/tier", json={"tier": 1}).status_code == 200
    assert client.put("/api/me/tier", json={"tier": 3}).json()["error"] == "tier_locked"


def test_freezes_and_comeback(client, clock):
    log_full(client, pick_first(client)["id"])          # Mon
    clock.day += timedelta(days=1)                       # Tue: busy, freeze it
    r = client.post("/api/freezes", json={})
    assert r.status_code == 201 and r.json()["freezes_left"] == 1
    assert client.post("/api/freezes", json={}).json()["error"] == "freeze_already_frozen"
    assert client.get("/api/today").json()["week"]["score"] == 2
    clock.day += timedelta(days=4)                       # Sat: Wed-Fri missed
    t = client.get("/api/today").json()
    assert t["days_since_last"] == 3
    out = log_full(client, pick_first(client)["id"])
    assert {"type": "comeback"} in out["events"]
    assert {"type": "title", "key": "comeback_kid"} in out["events"]


def test_yesterdays_plan_can_be_logged_next_day(client, clock):
    entry = pick_first(client)
    clock.day += timedelta(days=1)
    t = client.get("/api/today").json()
    assert [p["id"] for p in t["pending"]] == [entry["id"]]
    log_full(client, entry["id"])
    assert client.get("/api/today").json()["pending"] == []
    clock.day += timedelta(days=5)
    entry2 = pick_first(client)
    clock.day += timedelta(days=3)
    r = client.post(f"/api/logs/{entry2['id']}/outcome", json={"completion": "full", "actual_suds": 10})
    assert r.json()["error"] == "outside_log_window"


def test_progress_and_history(client, clock):
    for actual in (40, 30):
        log_full(client, pick_first(client)["id"], actual=actual)
        clock.day += timedelta(days=1)
    p = client.get("/api/progress").json()
    assert len(p["weeks"]) == 8
    assert p["weeks"][-1]["approaches"] == 2 and p["weeks"][-1]["mean_gap"] == 15.0
    assert p["totals"]["pct_full"] == 100
    assert p["gap_by_tier"]["1"]["mean"] == 15.0
    h = client.get("/api/history").json()
    assert len(h) == 2 and h[0]["date"] > h[1]["date"]
    titles = client.get("/api/titles").json()
    assert len(titles) == 10 and titles[0]["key"] == "rookie_nod" and titles[0]["earned_at"]


def test_web_client_served(client):
    r = client.get("/")
    assert r.status_code == 200 and "<html" in r.text.lower()
