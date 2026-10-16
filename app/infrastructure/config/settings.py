from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    DATABASE_URL: str = "postgresql+asyncpg://noteplus:noteplus@localhost:5432/noteplus"
    SYNC_DATABASE_URL: str = "postgresql+psycopg2://noteplus:noteplus@localhost:5432/noteplus"

    JWT_SECRET: str = "dev-jwt-secret-change-in-production-32chars!!"
    JWT_REFRESH_SECRET: str = "dev-refresh-secret-change-in-production-32chars!!"
    JWT_EXPIRES_IN_MINUTES: int = 60
    JWT_REFRESH_EXPIRES_IN_DAYS: int = 7

    PORT: int = 8000
    CORS_ORIGIN: str = "http://localhost:5173"
    CORS_ORIGINS: str = ""
    COOKIE_SAMESITE: str = "lax"
    DB_SSL: bool = False
    RATE_LIMIT_WINDOW_SECONDS: int = 900
    RATE_LIMIT_MAX_REQUESTS: int = 10
    ENV: str = "development"

    @property
    def is_dev(self) -> bool:
        return self.ENV != "production"

    @property
    def cookie_samesite(self) -> str:
        """Normalizado para Starlette: lax | strict | none.

        Cross-site (front en Vercel + API en Render) exige `none` (+ Secure).
        """
        v = self.COOKIE_SAMESITE.strip().lower()
        return v if v in ("lax", "strict", "none") else "lax"

    @property
    def allowed_origins(self) -> list[str]:
        """CORS_ORIGINS (coma) + CORS_ORIGIN legacy. En dev suma localhost."""
        origins = [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]
        if self.CORS_ORIGIN.strip() not in origins:
            origins.append(self.CORS_ORIGIN.strip())
        if self.is_dev:
            for extra in ("http://localhost:5173", "http://127.0.0.1:5173"):
                if extra not in origins:
                    origins.append(extra)
        return origins


settings = Settings()
