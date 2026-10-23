from datetime import date
from typing import Literal

from app.presentation.http.schemas.base import CamelModel


class UpdateClaseRequest(CamelModel):
    fecha: date | None = None
    hora: str | None = None  # HH:mm
    modalidad: Literal["PRESENCIAL", "VIRTUAL"] | None = None
    realizada: bool | None = None
    observacion: str | None = None


class FichaRef(CamelModel):
    id: str
    nombre: str
    codigo: str
    trimestre: str | None = None


class ClaseResponse(CamelModel):
    id: str
    ficha_id: str
    ficha_codigo: str | None = None
    ficha_nombre: str | None = None
    ficha: FichaRef | None = None
    fecha: date
    hora: str
    hora_fin: str | None = None
    duracion_minutos: int | None = None
    modalidad: str
    realizada: bool
    observacion: str | None = None
