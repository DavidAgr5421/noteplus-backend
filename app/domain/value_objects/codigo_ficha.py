from dataclasses import dataclass

from app.domain.errors import ValidationError


@dataclass(frozen=True, slots=True)
class CodigoFicha:
    value: str

    @classmethod
    def create(cls, raw: str) -> "CodigoFicha":
        trimmed = raw.strip()
        if not trimmed:
            raise ValidationError("El código de ficha es requerido")
        if len(trimmed) > 50:
            raise ValidationError("El código de ficha no puede exceder 50 caracteres")
        return cls(value=trimmed)

    def __str__(self) -> str:
        return self.value
