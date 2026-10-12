from pydantic import field_validator
from app.presentation.http.schemas.base import CamelModel
import re

_EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


class RegisterRequest(CamelModel):
    nombre: str
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        if not _EMAIL_RE.match(v.strip().lower()):
            raise ValueError("Email inválido")
        return v.strip().lower()

    @field_validator("nombre")
    @classmethod
    def validate_nombre(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Nombre requerido")
        return v.strip()

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Mínimo 8 caracteres")
        return v


class LoginRequest(CamelModel):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        if not _EMAIL_RE.match(v.strip().lower()):
            raise ValueError("Email inválido")
        return v.strip().lower()


class TokenResponse(CamelModel):
    access_token: str
    token_type: str = "bearer"


class InstructorResponse(CamelModel):
    id: str
    nombre: str
    email: str


class AuthResponse(CamelModel):
    """Frontend contract: { accessToken, user }. Serializes camelCase."""

    access_token: str
    token_type: str = "bearer"
    user: InstructorResponse
