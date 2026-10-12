from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.infrastructure.security.jwt_service import JwtTokenService

_bearer = HTTPBearer(auto_error=False)
_jwt = JwtTokenService()


async def get_current_instructor(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> dict:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="No autorizado")
    try:
        payload = _jwt.verify_access_token(credentials.credentials)
        return payload
    except Exception:
        raise HTTPException(status_code=401, detail="No autorizado")


async def require_auth(request: Request) -> dict:
    """Dependency for protected routes — returns instructor payload."""
    auth = request.headers.get("Authorization")
    if not auth or not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="No autorizado")
    token = auth[7:]
    try:
        return _jwt.verify_access_token(token)
    except Exception:
        raise HTTPException(status_code=401, detail="No autorizado")
