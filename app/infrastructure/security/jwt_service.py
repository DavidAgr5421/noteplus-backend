from datetime import UTC, datetime, timedelta

from jose import JWTError, jwt

from app.domain.errors import UnauthorizedError
from app.infrastructure.config.settings import settings


class JwtTokenService:
    def __init__(
        self,
        access_secret: str | None = None,
        refresh_secret: str | None = None,
        access_minutes: int | None = None,
        refresh_days: int | None = None,
    ) -> None:
        self.access_secret = access_secret or settings.JWT_SECRET
        self.refresh_secret = refresh_secret or settings.JWT_REFRESH_SECRET
        self.access_minutes = access_minutes or settings.JWT_EXPIRES_IN_MINUTES
        self.refresh_days = refresh_days or settings.JWT_REFRESH_EXPIRES_IN_DAYS

    def generate_access_token(self, instructor_id: str, email: str) -> str:
        exp = datetime.now(UTC) + timedelta(minutes=self.access_minutes)
        return jwt.encode(
            {"sub": instructor_id, "email": email, "exp": exp},
            self.access_secret,
            algorithm="HS256",
        )

    def generate_refresh_token(self, instructor_id: str, email: str) -> str:
        exp = datetime.now(UTC) + timedelta(days=self.refresh_days)
        return jwt.encode(
            {"sub": instructor_id, "email": email, "exp": exp},
            self.refresh_secret,
            algorithm="HS256",
        )

    def verify_access_token(self, token: str) -> dict:
        try:
            payload = jwt.decode(token, self.access_secret, algorithms=["HS256"])
            return {"instructor_id": payload["sub"], "email": payload["email"]}
        except (JWTError, KeyError):
            raise UnauthorizedError("Token inválido o expirado")

    def verify_refresh_token(self, token: str) -> dict:
        try:
            payload = jwt.decode(token, self.refresh_secret, algorithms=["HS256"])
            return {"instructor_id": payload["sub"], "email": payload["email"]}
        except (JWTError, KeyError):
            raise UnauthorizedError("Refresh token inválido o expirado")
