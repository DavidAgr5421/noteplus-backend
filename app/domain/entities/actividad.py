from dataclasses import dataclass
from datetime import date, datetime


@dataclass(slots=True)
class Actividad:
    id: str
    ficha_id: str
    parent_id: str | None
    nombre: str
    fecha_limite: date | None
    porcentaje: float
    orden: int
    created_at: datetime
    updated_at: datetime

    def is_root(self) -> bool:
        return self.parent_id is None
