from datetime import UTC, datetime

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
async def health():
    return {"status": "ok", "timestamp": datetime.now(UTC).isoformat()}


@router.get("/health/db")
async def health_db():
    # Fase 0: placeholder, will check DB in later phases
    return {"status": "ok", "db": "not_checked_yet"}
