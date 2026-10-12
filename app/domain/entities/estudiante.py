from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class Estudiante:
    id: str
    ficha_id: str
    nombre: str
    identificacion: str
    email: str | None
    created_at: datetime
    updated_at: datetime
    tipo_identificacion: str = "CC"
    contacto: str | None = None
