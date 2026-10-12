from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from app.infrastructure.persistence.database import AsyncSessionLocal
from app.infrastructure.security.jwt_service import JwtTokenService

_bearer = HTTPBearer(auto_error=False)
_jwt = JwtTokenService()


async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_current_instructor(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: AsyncSession = Depends(get_db),  # ensure DB available but not used here
) -> dict:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="No autorizado")
    try:
        payload = _jwt.verify_access_token(credentials.credentials)
        return payload
    except Exception:
        raise HTTPException(status_code=401, detail="No autorizado")


# Alternative: read from Authorization header manually for tests
async def get_current_instructor_from_request(request: Request) -> dict:
    auth = request.headers.get("Authorization")
    if not auth or not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="No autorizado")
    token = auth[7:]
    try:
        return _jwt.verify_access_token(token)
    except Exception:
        raise HTTPException(status_code=401, detail="No autorizado")
