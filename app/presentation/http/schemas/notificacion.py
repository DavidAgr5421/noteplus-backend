from datetime import date
from app.presentation.http.schemas.base import CamelModel


class Notificacion(CamelModel):
    id: str
    tipo: str  # clase_proxima | actividad_por_expirar | ficha_culminada
    titulo: str
    mensaje: str
    link: str
    fecha: date | None = None


class NotificacionesResponse(CamelModel):
    notificaciones: list[Notificacion]
