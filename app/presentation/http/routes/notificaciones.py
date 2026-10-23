from datetime import datetime, timedelta

import pytz
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.persistence.repositories.actividad_repository import (
    SqlAlchemyActividadRepository,
)
from app.infrastructure.persistence.repositories.clase_repository import SqlAlchemyClaseRepository
from app.infrastructure.persistence.repositories.ficha_repository import SqlAlchemyFichaRepository
from app.presentation.http.dependencies import get_current_instructor, get_db
from app.presentation.http.schemas.notificacion import Notificacion, NotificacionesResponse

router = APIRouter(prefix="/notificaciones", tags=["notificaciones"])

# RN-10 America/Bogota, igual que el resto de la app
TZ = pytz.timezone("America/Bogota")
AVISO_CLASE_HORAS = 12
AVISO_ACTIVIDAD_DIAS = 4


def _parse_hora(hora: str | None) -> tuple[int, int] | None:
    try:
        h, m = (hora or "")[:5].split(":")
        return int(h), int(m)
    except (ValueError, AttributeError):
        return None


@router.get("", response_model=NotificacionesResponse)
async def list_notificaciones(db: AsyncSession = Depends(get_db), current=Depends(get_current_instructor)):
    instructor_id = current["instructor_id"]
    now = datetime.now(TZ)
    today = now.date()
    limite_clase = now + timedelta(hours=AVISO_CLASE_HORAS)
    limite_actividad = today + timedelta(days=AVISO_ACTIVIDAD_DIAS)

    ficha_repo = SqlAlchemyFichaRepository(db)
    actividad_repo = SqlAlchemyActividadRepository(db)
    clase_repo = SqlAlchemyClaseRepository(db)

    notificaciones: list[Notificacion] = []

    # 1. Clases próximas a iniciar (próximas 12 horas)
    proximas = await clase_repo.find_by_instructor_range(instructor_id, today, today + timedelta(days=1))
    ficha_nombres: dict[str, str] = {}
    if proximas:
        from sqlalchemy import select

        from app.infrastructure.persistence.models.ficha_model import FichaModel

        result = await db.execute(select(FichaModel).where(FichaModel.id.in_(list({c.ficha_id for c in proximas}))))
        ficha_nombres = {f.id: f.nombre for f in result.scalars().all()}
    candidatas = []
    for c in proximas:
        hm = _parse_hora(c.hora)
        if not hm:
            continue
        inicio = TZ.localize(datetime(c.fecha.year, c.fecha.month, c.fecha.day, hm[0], hm[1]))
        if now < inicio <= limite_clase:
            candidatas.append((inicio, c))
    candidatas.sort(key=lambda t: t[0])
    for inicio, c in candidatas:
        nombre = ficha_nombres.get(c.ficha_id, "Ficha")
        notificaciones.append(Notificacion(
            id=f"clase:{c.id}",
            tipo="clase_proxima",
            titulo="Clase próxima a iniciar",
            mensaje=f"{nombre} · hoy {inicio.strftime('%H:%M')}" if inicio.date() == today else f"{nombre} · mañana {inicio.strftime('%H:%M')}",
            link=f"/clases/{c.id}/asistencias",
            fecha=c.fecha,
        ))

    # 2. Actividades por expirar (hoy hasta dentro de 4 días, aviso constante)
    fichas = await ficha_repo.find_by_instructor(instructor_id, False)
    fichas_activas = [f for f in fichas if not f.finalizada]
    por_expirar = []
    for f in fichas_activas:
        acts = await actividad_repo.find_by_ficha(f.id)
        for a in acts:
            if a.fecha_limite and today <= a.fecha_limite <= limite_actividad:
                por_expirar.append((a.fecha_limite, f, a))
    por_expirar.sort(key=lambda t: (t[0], t[1].nombre))
    for fecha_lim, f, a in por_expirar:
        dias = (fecha_lim - today).days
        cuando = "hoy" if dias == 0 else "mañana" if dias == 1 else f"en {dias} días"
        notificaciones.append(Notificacion(
            id=f"actividad:{a.id}",
            tipo="actividad_por_expirar",
            titulo="Actividad por expirar",
            mensaje=f"{a.nombre} ({f.nombre}) vence {cuando}",
            link=f"/fichas/{f.id}/actividades",
            fecha=fecha_lim,
        ))

    # 3. Fichas con clases culminadas (todas con fecha pasada, sin finalizar)
    for f in fichas_activas:
        clases = await clase_repo.find_by_ficha(f.id)
        if clases and all(c.fecha <= today for c in clases):
            notificaciones.append(Notificacion(
                id=f"ficha-culminada:{f.id}",
                tipo="ficha_culminada",
                titulo="Ficha con clases culminadas",
                mensaje=f"{f.nombre} terminó sus {len(clases)} clases. Podés finalizarla o hacer modificaciones.",
                link=f"/fichas/{f.id}",
                fecha=max(c.fecha for c in clases),
            ))

    return NotificacionesResponse(notificaciones=notificaciones)
