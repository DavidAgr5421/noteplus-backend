from typing import Literal

from app.presentation.http.schemas.base import CamelModel


class AsistenciaItem(CamelModel):
    estudiante_id: str
    estado: Literal["ASISTIO", "NO_ASISTIO"]
    justificacion: str | None = None


class SaveAsistenciasRequest(CamelModel):
    asistencias: list[AsistenciaItem]
    observacion: str | None = None


class AsistenciaResponse(CamelModel):
    id: str
    clase_id: str
    estudiante_id: str
    estudiante_nombre: str | None = None
    estado: str
    justificacion: str | None = None
