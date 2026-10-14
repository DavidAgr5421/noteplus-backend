from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import date, datetime
import pytz

from app.presentation.http.dependencies import get_db, get_current_instructor
from app.presentation.http.schemas.clase import UpdateClaseRequest, ClaseResponse
from app.infrastructure.persistence.models.clase_model import ClaseModel
from app.infrastructure.persistence.models.ficha_model import FichaModel
from app.infrastructure.persistence.models.horario_ficha_model import HorarioFichaModel
from app.infrastructure.persistence.repositories.clase_repository import SqlAlchemyClaseRepository
from app.infrastructure.persistence.repositories.ficha_repository import SqlAlchemyFichaRepository

router = APIRouter(prefix="/clases", tags=["clases"])


def _sumar_minutos(hora: str, minutos: int) -> str | None:
    """Suma minutos a una hora HH:mm. Devuelve None si el formato es inválido."""
    try:
        h, m = hora[:5].split(":")
        total = int(h) * 60 + int(m) + minutos
        return f"{(total // 60) % 24:02d}:{total % 60:02d}"
    except (ValueError, AttributeError):
        return None


def _duracion_para(fecha: date, hora: str, horarios: list) -> int | None:
    """Duración del horario de la ficha que originó la clase (día semana + hora)."""
    domain_dia = (fecha.weekday() + 1) % 7  # 0=domingo, igual que RN-03
    prefix = hora[:5]
    for h in horarios:
        if h.dia_semana == domain_dia and (h.hora or "")[:5] == prefix:
            return h.duracion_minutos
    return None


async def _horarios_map(db: AsyncSession, ficha_ids: set) -> dict:
    if not ficha_ids:
        return {}
    result = await db.execute(
        select(HorarioFichaModel).where(HorarioFichaModel.ficha_id.in_(list(ficha_ids)))
    )
    grouped: dict = {}
    for h in result.scalars().all():
        grouped.setdefault(h.ficha_id, []).append(h)
    return grouped


def _to_resp(c: ClaseModel, ficha_map: dict | None = None, horarios_map: dict | None = None) -> ClaseResponse:
    ficha = ficha_map.get(c.ficha_id) if ficha_map else None
    horarios = (horarios_map or {}).get(c.ficha_id, [])
    duracion = _duracion_para(c.fecha, c.hora, horarios)
    return ClaseResponse(
        id=c.id,
        ficha_id=c.ficha_id,
        ficha_codigo=ficha.codigo if ficha else None,
        ficha_nombre=ficha.nombre if ficha else None,
        ficha={"id": ficha.id, "nombre": ficha.nombre, "codigo": ficha.codigo,
               "trimestre": getattr(ficha, "trimestre", None)} if ficha else None,
        fecha=c.fecha,
        hora=c.hora,
        hora_fin=_sumar_minutos(c.hora, duracion) if duracion else None,
        duracion_minutos=duracion,
        modalidad=c.modalidad,
        realizada=c.realizada,
        observacion=c.observacion,
    )


@router.get("", response_model=list[ClaseResponse])
async def list_clases(
    from_date: date | None = Query(None, alias="from"),
    to_date: date | None = Query(None, alias="to"),
    db: AsyncSession = Depends(get_db),
    current=Depends(get_current_instructor),
):
    repo = SqlAlchemyClaseRepository(db)
    clases = await repo.find_by_instructor_range(current["instructor_id"], from_date, to_date)
    # fetch fichas for mapping
    if clases:
        ficha_ids = {c.ficha_id for c in clases}
        result = await db.execute(select(FichaModel).where(FichaModel.id.in_(list(ficha_ids))))
        ficha_map = {f.id: f for f in result.scalars().all()}
        horarios_map = await _horarios_map(db, ficha_ids)
    else:
        ficha_map = {}
        horarios_map = {}
    return [_to_resp(c, ficha_map, horarios_map) for c in clases]


@router.get("/today", response_model=list[ClaseResponse])
async def today_clases(db: AsyncSession = Depends(get_db), current=Depends(get_current_instructor)):
    # RN-10 America/Bogota
    tz = pytz.timezone("America/Bogota")
    today = datetime.now(tz).date()
    repo = SqlAlchemyClaseRepository(db)
    clases = await repo.find_today(current["instructor_id"], today)
    if clases:
        ficha_ids = {c.ficha_id for c in clases}
        result = await db.execute(select(FichaModel).where(FichaModel.id.in_(list(ficha_ids))))
        ficha_map = {f.id: f for f in result.scalars().all()}
        horarios_map = await _horarios_map(db, ficha_ids)
    else:
        ficha_map = {}
        horarios_map = {}
    return [_to_resp(c, ficha_map, horarios_map) for c in clases]


@router.get("/{clase_id}", response_model=ClaseResponse)
async def get_clase(clase_id: str, db: AsyncSession = Depends(get_db), current=Depends(get_current_instructor)):
    clase = await db.get(ClaseModel, clase_id)
    if not clase:
        raise HTTPException(status_code=404, detail="Clase no encontrada")
    # RN-01 check ownership via ficha
    ficha_repo = SqlAlchemyFichaRepository(db)
    ficha = await ficha_repo.find_by_id_and_instructor(clase.ficha_id, current["instructor_id"])
    if not ficha:
        raise HTTPException(status_code=404, detail="Clase no encontrada")
    horarios_map = await _horarios_map(db, {clase.ficha_id})
    return _to_resp(clase, {ficha.id: ficha}, horarios_map)


@router.patch("/{clase_id}", response_model=ClaseResponse)
async def update_clase(clase_id: str, payload: UpdateClaseRequest, db: AsyncSession = Depends(get_db), current=Depends(get_current_instructor)):
    clase = await db.get(ClaseModel, clase_id)
    if not clase:
        raise HTTPException(status_code=404, detail="Clase no encontrada")
    # RN-01 check ownership via ficha
    ficha_repo = SqlAlchemyFichaRepository(db)
    ficha = await ficha_repo.find_by_id_and_instructor(clase.ficha_id, current["instructor_id"])
    if not ficha:
        raise HTTPException(status_code=404, detail="Clase no encontrada")
    if ficha.archivada:
        raise HTTPException(status_code=409, detail="Ficha archivada es de solo lectura")

    if payload.fecha is not None:
        clase.fecha = payload.fecha
    if payload.hora is not None:
        clase.hora = payload.hora
    if payload.modalidad is not None:
        clase.modalidad = payload.modalidad
    if payload.realizada is not None:
        # `realizada` la decide el docente (incluso antes de la fecha).
        clase.realizada = payload.realizada
    if payload.observacion is not None:
        clase.observacion = payload.observacion

    await db.flush()
    await db.refresh(clase)
    horarios_map = await _horarios_map(db, {clase.ficha_id})
    return _to_resp(clase, {ficha.id: ficha}, horarios_map)
