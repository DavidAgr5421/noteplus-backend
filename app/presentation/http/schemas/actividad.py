from pydantic import field_validator
from datetime import date
from app.presentation.http.schemas.base import CamelModel


class CreateActividadRequest(CamelModel):
    nombre: str
    porcentaje: float
    parent_id: str | None = None
    fecha_limite: date | None = None
    orden: int = 0

    @field_validator("nombre")
    @classmethod
    def not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("nombre requerido")
        return v.strip()

    @field_validator("porcentaje")
    @classmethod
    def check_porcentaje(cls, v: float) -> float:
        if v <= 0 or v > 100:
            raise ValueError("porcentaje entre 0 y 100")
        return v


class UpdateActividadRequest(CamelModel):
    nombre: str | None = None
    porcentaje: float | None = None
    fecha_limite: date | None = None
    orden: int | None = None


class ActividadResponse(CamelModel):
    id: str
    ficha_id: str
    parent_id: str | None = None
    nombre: str
    porcentaje: float
    fecha_limite: date | None = None
    orden: int
    nota_promedio: float | None = None


class CalificacionItem(CamelModel):
    estudiante_id: str
    nota: float

    @field_validator("nota")
    @classmethod
    def check_nota(cls, v: float) -> float:
        if v < 0 or v > 5:
            raise ValueError("nota entre 0 y 5")
        scaled = round(v * 10)
        if abs(scaled / 10 - v) > 1e-9:
            raise ValueError("nota máximo un decimal")
        return v


class SaveCalificacionesRequest(CamelModel):
    calificaciones: list[CalificacionItem]


class NotaEstudiante(CamelModel):
    estudiante_id: str
    estudiante_nombre: str
    identificacion: str
    nota_final: float
    nota_acumulada: float | None = None
    estado: str  # APROBADO | NO_APROBADO
    detalle: list[dict] = []


class NotasResponse(CamelModel):
    ficha_id: str
    nota_minima_aprobacion: float
    actividades: list[ActividadResponse]
    notas: list[NotaEstudiante]
