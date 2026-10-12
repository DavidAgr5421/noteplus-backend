from dataclasses import dataclass

from app.domain.errors import ValidationError


@dataclass(frozen=True, slots=True)
class Porcentaje:
    """RN-12: porcentaje 0–100 relativo al padre o a la nota final."""

    value: float

    @classmethod
    def create(cls, raw: float) -> "Porcentaje":
        if not isinstance(raw, (int, float)):
            raise ValidationError("El porcentaje debe ser un número", {"porcentaje": raw})
        v = float(raw)
        if v != v:
            raise ValidationError("El porcentaje debe ser un número", {"porcentaje": raw})
        if v <= 0 or v > 100:
            raise ValidationError(
                "El porcentaje debe estar entre 0 y 100 (exclusive 0)",
                {"porcentaje": raw},
            )
        return cls(value=v)
