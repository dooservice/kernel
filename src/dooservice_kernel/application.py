from __future__ import annotations

from collections.abc import AsyncIterator, Mapping, Sequence
from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from .config import Config
from .constants import OAUTH_STATE_TTL_SECONDS
from .db import DatabaseEngine
from .discovery import ModuleSelection
from .events import EventBridge
from .extensions import Extension
from .health import Boundary, HealthController
from .http import RequestContextMiddleware
from .logging import LoggingSetup
from .migrations import MigrationRunner
from .ports import Ports
from .problems import ProblemRenderer
from .profile import Profile
from .registry import Module, ModuleRegistry
from .security import CookieSigner, PasswordHasher

log = logging.getLogger(__name__)


class ApplicationBuilder:
    """Assembles the FastAPI app from the enabled modules. The only place that knows
    the boot order: logging → boundaries → database/migrations → module startup → listeners.

    `state` is what the application puts on `app.state` for its modules besides what the
    kernel puts there itself; `boundaries` are opened and closed around everything else.
    """

    def __init__(
        self,
        config: Config,
        modules: Sequence[Module],
        profile: Profile | None = None,
        boundaries: Sequence[Boundary] = (),
        state: Mapping[str, object] | None = None,
        use_generated_schemas: bool = False,
        extensions: Sequence[Extension] = (),
        bridge: EventBridge | None = None,
    ) -> None:
        self.config = config
        self.registry = ModuleRegistry(ModuleSelection(config.modules).apply(modules))
        self.boundaries = tuple(boundaries)
        self.state = dict(state or {})
        self.use_generated_schemas = use_generated_schemas
        self.extensions = tuple(extensions)
        self.bridge = bridge
        self.profile = profile or Profile()
        self.engine = DatabaseEngine(config.database.url, self.registry.orm_model_modules(), self.profile.migrations)

    def build(self) -> FastAPI:
        app = FastAPI(
            title=self.profile.title,
            debug=self.config.server.debug,
            lifespan=self.lifespan,
        )
        app.state.config = self.config
        app.state.registry = self.registry
        app.state.events = self.registry.events(self.bridge)
        app.state.ports = Ports()
        app.state.cookie_signer = CookieSigner(self.config.session.secret)
        app.state.password_hasher = PasswordHasher()
        for name, value in self.state.items():
            setattr(app.state, name, value)

        app.add_middleware(RequestContextMiddleware)
        app.add_middleware(
            SessionMiddleware,
            secret_key=self.config.session.secret,
            session_cookie=self.profile.state_cookie,
            max_age=OAUTH_STATE_TTL_SECONDS,
            same_site="lax",
            https_only=self.config.session.cookie_secure,
        )
        app.add_middleware(
            CORSMiddleware,
            allow_origins=self.config.cors.origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        ProblemRenderer().register(app)
        for extension in self.extensions:
            extension.install(app, self.boundaries)

        app.include_router(HealthController(self.boundaries, self.registry.health_checks()).router)
        for router in self.registry.routers():
            app.include_router(router, prefix=self.profile.api_prefix)
        for router in self.registry.root_routers():
            app.include_router(router)
        return app

    @asynccontextmanager
    async def lifespan(self, app: FastAPI) -> AsyncIterator[None]:
        LoggingSetup.configure(self.config.server.debug, self.config.server.log_format == "json")
        for boundary in self.boundaries:
            await boundary.connect()
        if self.use_generated_schemas:
            await self.engine.init()
            await self.engine.create_schemas()
        else:
            await MigrationRunner(self.engine, self.profile.baseline).ensure_schema()
            await self.engine.init()
        await self.registry.run_startup(app)
        listeners = self.registry.listeners(app)
        for listener in listeners:
            await listener.start()
        log.info("%s started with modules: %s", self.profile.title, [module.name for module in self.registry.modules])
        yield
        for listener in reversed(listeners):
            await listener.stop()
        await self.engine.close()
        for boundary in reversed(self.boundaries):
            await boundary.close()
