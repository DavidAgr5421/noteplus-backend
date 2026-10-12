from dataclasses import dataclass
from datetime import datetime
from typing import Literal

EstadoAsistencia = Literal["ASISTIO", "NO_ASISTIO"]


@dataclass(slots=True)
class Asistencia:
    id: str
    clase_id: str
    estudiante_id: str
    estado: EstadoAsistencia
    justificacion: str | None
    created_at: datetime
    updated_at: datetime
