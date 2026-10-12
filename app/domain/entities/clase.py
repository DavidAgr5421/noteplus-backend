from dataclasses import dataclass
from datetime import date, datetime
from typing import Literal

ModalidadClase = Literal["PRESENCIAL", "VIRTUAL"]


@dataclass(slots=True)
class Clase:
    id: str
    ficha_id: str
    fecha: date
    hora: str  # HH:mm
    modalidad: ModalidadClase
    realizada: bool
    observacion: str | None
    created_at: datetime
    updated_at: datetime

    def can_register_attendance(self) -> bool:
        return self.realizada
