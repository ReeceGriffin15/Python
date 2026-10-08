"""FastAPI adapter: JSON API under /api, static web client at /."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import asynccontextmanager
from datetime import date, datetime
from zoneinfo import ZoneInfo

from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session, sessionmaker

from ..config import Settings, load_settings
from ..db.repo import Repo
from ..db.session import init_db, make_engine
from ..seed.loader import ensure_default_user, seed_challenges
from ..services import JarService, ServiceError
from .schemas import FreezeIn, OutcomeIn, PickIn, TierIn


def create_app(settings: Settings | None = None, clock=None) -> FastAPI:
    """``clock`` returns "now" as an aware datetime; injectable for tests."""
    settings = settings or load_settings()
    clock = clock or (lambda tz: datetime.now(tz))
    engine = make_engine(settings.database_url)
    Sessions: sessionmaker[Session] = init_db(engine)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        with Sessions() as s:
            seed_challenges(s)
            ensure_default_user(s, settings.timezone)
        yield
        engine.dispose()

    app = FastAPI(title="Social Challenge Jar", version="0.1.0", lifespan=lifespan)

    def db() -> Iterator[Session]:
        with Sessions() as s:
            yield s

    def current_user_id() -> int:
        # Single-user MVP. Swap for real auth (session/JWT) later; everything
        # downstream is already scoped by this id.
        return 1

    def service(s: Session = Depends(db), user_id: int = Depends(current_user_id)) -> JarService:
        repo = Repo(s, user_id)
        today: date = clock(ZoneInfo(repo.user().timezone)).date()
        return JarService(repo, settings.rules, today)

    @app.exception_handler(ServiceError)
    async def _service_error(_: Request, exc: ServiceError):
        return JSONResponse({"error": exc.code}, status_code=exc.status)

    @app.get("/api/today")
    def today(svc: JarService = Depends(service)):
        return svc.today_state()

    @app.get("/api/options")
    def options(easier: bool = False, svc: JarService = Depends(service)):
        return svc.options(easier=easier)

    @app.post("/api/plans", status_code=201)
    def pick(body: PickIn, svc: JarService = Depends(service)):
        return svc.pick(**body.model_dump())

    @app.delete("/api/plans/{log_id}", status_code=204)
    def unpick(log_id: int, svc: JarService = Depends(service)):
        svc.unpick(log_id)

    @app.post("/api/logs/{log_id}/outcome")
    def outcome(log_id: int, body: OutcomeIn, svc: JarService = Depends(service)):
        return svc.log_outcome(log_id, **body.model_dump())

    @app.post("/api/freezes", status_code=201)
    def freeze(body: FreezeIn, svc: JarService = Depends(service)):
        return svc.use_freeze(body.date)

    @app.get("/api/progress")
    def progress(weeks: int = 8, svc: JarService = Depends(service)):
        return svc.progress(weeks=max(1, min(weeks, 52)))

    @app.get("/api/history")
    def history(limit: int = 30, svc: JarService = Depends(service)):
        return svc.history(limit=max(1, min(limit, 365)))

    @app.get("/api/titles")
    def titles(svc: JarService = Depends(service)):
        return svc.titles()

    @app.get("/api/challenges")
    def challenges(svc: JarService = Depends(service)):
        return svc.catalogue()

    @app.put("/api/me/tier")
    def set_tier(body: TierIn, svc: JarService = Depends(service)):
        return svc.set_tier(body.tier)

    if settings.web_dir.is_dir():
        app.mount("/", StaticFiles(directory=settings.web_dir, html=True), name="web")

    return app

