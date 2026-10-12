from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class Calificacion:
    id: str
    actividad_id: str
    estudiante_id: str
    nota: float
    created_at: datetime
    updated_at: datetime
