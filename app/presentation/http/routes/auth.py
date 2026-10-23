import time
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.config.settings import settings
from app.infrastructure.persistence.models.instructor_model import InstructorModel
from app.infrastructure.security.jwt_service import JwtTokenService
from app.infrastructure.security.password_hasher import BcryptPasswordHasher
from app.presentation.http.dependencies import get_current_instructor, get_db
from app.presentation.http.schemas.auth import InstructorResponse, LoginRequest, RegisterRequest

router = APIRouter(prefix="/auth", tags=["auth"])
hasher = BcryptPasswordHasher()
jwt = JwtTokenService()

# Simple in-memory rate limit: (ip, email) -> list[timestamps]
_rate_store: dict[str, list[float]] = defaultdict(list)


def check_rate_limit(ip: str, email: str):
    key = f"{ip}:{email.lower()}"
    now = time.time()
    window = settings.RATE_LIMIT_WINDOW_SECONDS
    max_req = settings.RATE_LIMIT_MAX_REQUESTS
    timestamps = _rate_store[key]
    # prune
    timestamps[:] = [t for t in timestamps if now - t < window]
    if len(timestamps) >= max_req:
        raise HTTPException(status_code=429, detail="Demasiadas solicitudes, intente más tarde")
    timestamps.append(now)


@router.post("/register", status_code=201)
async def register(payload: RegisterRequest, response: Response, db: AsyncSession = Depends(get_db)):
    # RN-21
    existing = await db.execute(select(InstructorModel).where(InstructorModel.email == payload.email.lower()))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email ya registrado")
    model = InstructorModel(
        nombre=payload.nombre.strip(),
        email=payload.email.lower(),
        password_hash=hasher.hash(payload.password),
    )
    db.add(model)
    await db.flush()
    await db.refresh(model)
    # Frontend contract: { accessToken, user } + refresh cookie (same as login)
    access = jwt.generate_access_token(model.id, model.email)
    refresh = jwt.generate_refresh_token(model.id, model.email)
    response.set_cookie(
        key="refresh_token",
        value=refresh,
        httponly=True,
        secure=False if settings.is_dev else True,
        samesite=settings.cookie_samesite,  # "none" en prod cross-site (Vercel→Render)
        max_age=settings.JWT_REFRESH_EXPIRES_IN_DAYS * 24 * 3600,
        path="/",
    )
    return {
        "accessToken": access,
        "tokenType": "bearer",
        "user": {"id": model.id, "nombre": model.nombre, "email": model.email},
    }


@router.post("/login")
async def login(payload: LoginRequest, request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    ip = request.client.host if request.client else "unknown"
    check_rate_limit(ip, payload.email)
    result = await db.execute(select(InstructorModel).where(InstructorModel.email == payload.email.lower()))
    instructor = result.scalar_one_or_none()
    if not instructor or not hasher.verify(payload.password, instructor.password_hash):
        raise HTTPException(status_code=401, detail="Credenciales inválidas")
    access = jwt.generate_access_token(instructor.id, instructor.email)
    refresh = jwt.generate_refresh_token(instructor.id, instructor.email)
    # RN-22 refresh in httpOnly cookie
    response.set_cookie(
        key="refresh_token",
        value=refresh,
        httponly=True,
        secure=False if settings.is_dev else True,  # Secure only in production
        samesite=settings.cookie_samesite,
        max_age=settings.JWT_REFRESH_EXPIRES_IN_DAYS * 24 * 3600,
        path="/",
    )
    # Frontend contract: { accessToken, user } (camelCase)
    return {
        "accessToken": access,
        "tokenType": "bearer",
        "user": {"id": instructor.id, "nombre": instructor.nombre, "email": instructor.email},
    }


@router.post("/refresh")
async def refresh(request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    # Try cookie then body
    token = request.cookies.get("refresh_token")
    if not token:
        body = {}
        try:
            body = await request.json()
        except Exception:
            pass
        token = body.get("refresh_token")
    if not token:
        raise HTTPException(status_code=401, detail="Refresh token requerido")
    try:
        payload = jwt.verify_refresh_token(token)
    except Exception:
        raise HTTPException(status_code=401, detail="Refresh token inválido")
    # Ensure instructor still exists
    instructor = await db.get(InstructorModel, payload["instructor_id"])
    if not instructor:
        raise HTTPException(status_code=401, detail="No autorizado")
    new_access = jwt.generate_access_token(instructor.id, instructor.email)
    new_refresh = jwt.generate_refresh_token(instructor.id, instructor.email)
    response.set_cookie(
        key="refresh_token",
        value=new_refresh,
        httponly=True,
        secure=False if settings.is_dev else True,
        samesite=settings.cookie_samesite,
        max_age=settings.JWT_REFRESH_EXPIRES_IN_DAYS * 24 * 3600,
        path="/",
    )
    return {"accessToken": new_access, "tokenType": "bearer"}


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie(
        key="refresh_token",
        path="/",
        secure=False if settings.is_dev else True,
        samesite=settings.cookie_samesite,
    )
    return {"message": "Sesión cerrada"}


@router.get("/me", response_model=InstructorResponse)
async def me(current=Depends(get_current_instructor), db: AsyncSession = Depends(get_db)):
    instructor = await db.get(InstructorModel, current["instructor_id"])
    if not instructor:
        raise HTTPException(status_code=404, detail="No encontrado")
    return InstructorResponse(id=instructor.id, nombre=instructor.nombre, email=instructor.email)
