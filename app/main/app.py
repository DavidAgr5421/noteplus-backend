from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from app.domain.errors import DomainError
from app.infrastructure.config.settings import settings

# Composition root — singletons
from app.infrastructure.security.jwt_service import JwtTokenService
from app.infrastructure.security.password_hasher import BcryptPasswordHasher
from app.infrastructure.time.system_clock import SystemClock
from app.presentation.http.middlewares.error_handler import (
    domain_error_handler,
    generic_error_handler,
    validation_error_handler,
)
from app.presentation.http.routes.actividades import router as actividades_router
from app.presentation.http.routes.asistencias import router as asistencias_router
from app.presentation.http.routes.auth import router as auth_router
from app.presentation.http.routes.clases import router as clases_router
from app.presentation.http.routes.estudiantes import router as estudiantes_router
from app.presentation.http.routes.fichas import router as fichas_router
from app.presentation.http.routes.health import router as health_router
from app.presentation.http.routes.notificaciones import router as notificaciones_router

jwt_service = JwtTokenService()
password_hasher = BcryptPasswordHasher()
clock = SystemClock()


def create_app() -> FastAPI:
    is_prod = not settings.is_dev
    app = FastAPI(
        title="NotePlus API",
        version="0.1.0",
        docs_url=None if is_prod else "/docs",
        redoc_url=None if is_prod else "/redoc",
        openapi_url=None if is_prod else "/openapi.json",
    )

    # CORS — never use "*" together with allow_credentials (browsers reject it)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Exception handlers
    app.add_exception_handler(DomainError, domain_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(RequestValidationError, validation_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, generic_error_handler)

    # Routes — all under /api/v1
    app.include_router(health_router, prefix="/api/v1")
    app.include_router(auth_router, prefix="/api/v1")
    app.include_router(fichas_router, prefix="/api/v1")
    app.include_router(estudiantes_router, prefix="/api/v1")
    app.include_router(clases_router, prefix="/api/v1")
    app.include_router(asistencias_router, prefix="/api/v1")
    app.include_router(actividades_router, prefix="/api/v1")
    app.include_router(notificaciones_router, prefix="/api/v1")

    # Expose singletons for DI in later phases
    app.state.jwt_service = jwt_service
    app.state.password_hasher = password_hasher
    app.state.clock = clock

    return app


app = create_app()
