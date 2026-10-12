import re
from dataclasses import dataclass

from app.domain.errors import ValidationError

_EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


@dataclass(frozen=True, slots=True)
class Email:
    value: str

    @classmethod
    def create(cls, raw: str) -> "Email":
        normalized = raw.strip().lower()
        if not _EMAIL_RE.match(normalized):
            raise ValidationError("Email inválido", {"email": raw})
        return cls(value=normalized)

    def __str__(self) -> str:
        return self.value
