"""InsightForge BI backend entrypoint."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api.analytics import router as analytics_router
from app.api.auth import limiter as auth_limiter
from app.api.auth import router as auth_router
from app.api.exports import router as exports_router
from app.api.health import router as health_router
from app.api.insights import router as insights_router
from app.api.uploads import router as uploads_router
from app.core.config import settings
from app.core.logging import configure_logging, get_logger
from app.core.middleware import RequestIDMiddleware

configure_logging(settings.LOG_LEVEL)
log = get_logger()


@asynccontextmanager
async def lifespan(_: FastAPI):
    log.info("backend_startup", cors=settings.cors_origins_list)
    yield


app = FastAPI(title="InsightForge BI API", version="0.1.0", docs_url="/docs", lifespan=lifespan)

app.add_middleware(RequestIDMiddleware)
# Starlette rejects allow_origins=["*"] combined with allow_credentials=True.
# In prod behind Nginx (same-origin /api) CORS is a no-op, so drop credentials for wildcard.
_cors_origins = settings.cors_origins_list
_allow_credentials = "*" not in _cors_origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.state.limiter = auth_limiter
# slowapi's handler signature is narrower than Starlette's protocol; safe at runtime.
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]

app.include_router(health_router, tags=["system"])
app.include_router(auth_router)
app.include_router(uploads_router)
app.include_router(analytics_router)
app.include_router(insights_router)
app.include_router(exports_router)
