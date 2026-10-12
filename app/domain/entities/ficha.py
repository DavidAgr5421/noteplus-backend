from dataclasses import dataclass
from datetime import date, datetime


@dataclass(slots=True)
class Ficha:
    id: str
    instructor_id: str
    codigo: str
    nombre: str
    fecha_inicio: date
    total_clases: int
    nota_minima_aprobacion: float
    archivada: bool
    finalizada: bool
    created_at: datetime
    updated_at: datetime

    def is_read_only(self) -> bool:
        return self.archivada

    def can_modify_grades(self) -> bool:
        return not self.finalizada and not self.archivada
