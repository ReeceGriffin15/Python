# Social Challenge Jar

A daily cue for graded, real-world social practice. Each morning you pick one small experiment from your current tier and write an if–then plan. In the evening you log how anxious you actually felt against what you predicted. Over time you can see the gap between the two shrink.

> Everyday practice homework, not therapy or a clinical treatment.

## Run it

```bash
cd social-challenge-jar
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
uvicorn challenge_jar.main:app --reload            # http://localhost:8000
pytest                                              # 32 tests
```

The SQLite file (`challenge_jar.db`) is created next to this README on first run, and the 56 seed challenges are loaded automatically.

**On your phone:** run `uvicorn challenge_jar.main:app --host 0.0.0.0` and open `http://<your-computer's-LAN-IP>:8000`, then use "Add to Home Screen". There's a web manifest, so it opens like an app. To reach it away from home, deploy the `Dockerfile` to a small host (Fly.io, Railway, a VPS) with a volume on `/data`. **Add auth before exposing it publicly** (see "Going multi-user" below).

### Settings (env vars)

| Var | Default | |
|---|---|---|
| `JAR_DATABASE_URL` | `sqlite:///./challenge_jar.db` | Any SQLAlchemy URL (Postgres later) |
| `JAR_TIMEZONE` | `Europe/London` | Used to decide what "today" is |
| `JAR_UNLOCK_N` | `5` | Full completions to unlock the next tier |
| `JAR_OPTIONS_PER_DAY` | `3` | Cards offered each morning |
| `JAR_FREEZES_PER_MONTH` | `2` | |
| `JAR_COMEBACK_GAP_DAYS` | `3` | Missed days before a return counts as a comeback |
| `JAR_WEEK_TARGET` | `5` | Approaches per week |

## The loop

1. **Morning:** 3 cards from the current tier only, spread across different categories. The draw is fixed for the day, so reloading can't reroll it. Each card shows the behaviour, the safety behaviour to drop, and what counts as done. Pick one, then the **when** and **where** fields (the if–then plan) are required. You also give a predicted SUDs score (0–100) and, optionally, what you're afraid will happen.
2. **Evening:** did it / partly / didn't, peak anxiety (actual SUDs), whether you dropped the safety behaviour, and a one-line note. The result screen frames it as a forecast check ("You predicted 60, it was 35"), never as a failed dare. Yesterday's plan can still be logged the next day.
3. **Unlock:** 5 *full* completions at tier *t* unlock *t+1*, strictly in order. You're moved up automatically and can step down any time from the **You** tab, but never above what you've unlocked.
4. **Low-energy day:** one tap switches to the tier below. It still counts as an approach for the week.
5. **Week score:** approaches + freezes this week, out of 5. There is no streak counter.
6. **Freezes:** 2 per calendar month. Each covers one missed day in the current week.
7. **Comeback:** an approach after 3+ uncovered days fires a comeback message and the *Comeback Kid* title. The Today screen greets you with "no catching up needed" instead of a count of missed days.
8. **Titles:** 10 milestones, all for showing up (approach counts, categories, safety behaviours dropped, comebacks). None rewards perfection.
9. **Progress:** one chart with two stacked panels on a shared week axis: approaches per week (with the target line) and the average prediction gap (expected − actual). It's two panels instead of a dual-axis chart because the units differ. There's also a table view, the gap per tier (earlier vs recent), and recent history.

**One deliberate change from the brief:** the *predicted* SUDs score is captured in the **morning**, at pick time, not in the evening. A prediction written down after the event gets coloured by what actually happened, and capturing it beforehand is the core of the behavioural-experiment method (Clark & Wells). If you skipped it in the morning, the evening form asks for it retrospectively.

## Architecture

```
challenge_jar/
  domain/        pure Python, no framework imports
    models.py      Challenge, Log, Completion, Category, tier SUDs bands
    rules.py       unlock, daily options, week summaries, freezes, miss runs/comebacks, gap stats
    titles.py      title rules, keyed by stable ids
  db/            SQLAlchemy tables + Repo (maps rows to domain objects, every query user-scoped)
  services.py    use-cases: today / pick / log outcome / freeze / progress / titles. Returns codes, not prose
  api/           FastAPI adapter (JSON under /api) + static web client at /
  seed/          challenges.json (56 cards) + idempotent loader (upserts by slug, retires removed ones)
web/             no-build client: vanilla JS modules
  theme.css      design tokens only (light + dark)
  app.css        components, which reference tokens only
  copy.js        every user-facing string, including title names and error messages
  chart.js       hand-rolled SVG chart, no chart library
tests/           domain rules, titles, seed validity, end-to-end API flow with a fake clock
```

**Why this stack:** Python matches the rest of this repo. FastAPI and SQLAlchemy give typed request validation and a database URL you can switch to Postgres. The client needs no build step, so there's nothing to maintain for a weekend MVP, and the JSON API means a React or native client could replace it later without touching the domain.

**Rebranding** means editing `theme.css` and `copy.js`, and possibly `app.css` for layout. The domain and API return keys (`"comeback"`, `"rookie_nod"`, `"freeze_none_left"`), never display text.

**Adding challenges:** edit `seed/challenges.json` and restart. The loader checks that slugs are unique, categories are valid, and each SUDs score falls inside its tier's band (T1 10–25, T2 25–40, T3 40–60, T4 60–80). Removed challenges are deactivated, not deleted, so history stays intact. Each log stores the tier it was picked at, so editing a card never rewrites unlock history.

### API

| Method | Path | |
|---|---|---|
| GET | `/api/today` | tier progress, today's entry or options, pending plans, week score, freezes |
| GET | `/api/options?easier=` | today's cards (or tier−1 cards) |
| POST | `/api/plans` | pick + if–then (+ prediction) |
| DELETE | `/api/plans/{id}` | change pick (before logging, today only) |
| POST | `/api/logs/{id}/outcome` | evening log. Returns events (`tier_unlocked`, `title`, `comeback`) |
| POST | `/api/freezes` | freeze a day this week |
| GET | `/api/progress?weeks=8` | weekly series, totals, gap by tier |
| GET | `/api/history`, `/api/titles`, `/api/challenges` | |
| PUT | `/api/me/tier` | step down, or back up to the unlocked tier |

Errors come back as `{"error": "<code>"}`, and `copy.js` maps each code to text.

### Going multi-user (later)

Every per-person table already has a `user_id`. To add accounts:

1. Replace `current_user_id()` in `api/app.py` with real auth (session cookie or OAuth).
2. Create a `users` row at sign-up.
3. Move to Postgres via `JAR_DATABASE_URL`, and add Alembic before the schema changes under real data.

The core loop doesn't change. Per-user rule overrides (such as a different unlock N) would mean passing a `Rules` built from the user's row in place of the global one.

## Success metrics to watch (6–8 weeks)

The Progress tab shows each of these:

- Approaches per week (≥5)
- % full completions
- Mean prediction gap per tier, earlier vs recent
- Tier unlocks without dropping off after misses (the comeback count)
