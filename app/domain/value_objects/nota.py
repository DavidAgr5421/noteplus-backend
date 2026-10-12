from dataclasses import dataclass

from app.domain.errors import ValidationError


@dataclass(frozen=True, slots=True)
class Nota:
    """RN-15: escala 0.0–5.0 con un decimal."""

    value: float

    @classmethod
    def create(cls, raw: float) -> "Nota":
        if not isinstance(raw, (int, float)):
            raise ValidationError("La nota debe ser un número", {"nota": raw})
        v = float(raw)
        if v != v:  # NaN
            raise ValidationError("La nota debe ser un número", {"nota": raw})
        if v < 0 or v > 5:
            raise ValidationError("La nota debe estar entre 0.0 y 5.0", {"nota": raw})
        scaled = round(v * 10)
        reconstructed = scaled / 10
        if abs(reconstructed - v) > 1e-9:
            raise ValidationError("La nota debe tener máximo un decimal", {"nota": raw})
        return cls(value=reconstructed)
