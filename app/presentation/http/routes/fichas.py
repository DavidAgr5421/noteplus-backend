from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import date
import uuid

from app.presentation.http.dependencies import get_db, get_current_instructor
from app.presentation.http.schemas.ficha import CreateFichaRequest, UpdateFichaRequest, FichaResponse, HorarioInput
from app.infrastructure.persistence.models.ficha_model import FichaModel
from app.infrastructure.persistence.models.horario_ficha_model import HorarioFichaModel
from app.infrastructure.persistence.models.clase_model import ClaseModel
from app.infrastructure.persistence.repositories.ficha_repository import SqlAlchemyFichaRepository
from app.infrastructure.persistence.repositories.actividad_repository import SqlAlchemyActividadRepository
from app.domain.services.class_schedule_generator import ClassScheduleGenerator, HorarioInput as DomainHorario

router = APIRouter(prefix="/fichas", tags=["fichas"])


def trimestre_de(fecha: date) -> str:
    """Trimestre calendario T1–T4 + año, derivado de la fecha de inicio."""
    return f"T{(fecha.month - 1) // 3 + 1} {fecha.year}"


def _to_response(ficha: FichaModel) -> FichaResponse:
    num_estudiantes = len(ficha.estudiantes) if hasattr(ficha, "estudiantes") and ficha.estudiantes is not None else 0
    if hasattr(ficha, "clases") and ficha.clases is not None and len(ficha.clases) > 0:
        clases_restantes = sum(1 for c in ficha.clases if not c.realizada)
    else:
        clases_restantes = ficha.total_clases

    return FichaResponse(
        id=ficha.id,
        codigo=ficha.codigo,
        nombre=ficha.nombre,
        fecha_inicio=ficha.fecha_inicio,
        trimestre=getattr(ficha, "trimestre", None) or trimestre_de(ficha.fecha_inicio),
        total_clases=ficha.total_clases,
        nota_minima_aprobacion=float(ficha.nota_minima_aprobacion),
        archivada=ficha.archivada,
        finalizada=ficha.finalizada,
        instructor_id=ficha.instructor_id,
        horarios=[
            HorarioInput(dia_semana=h.dia_semana, hora=h.hora, duracion_minutos=h.duracion_minutos)
            for h in (ficha.horarios or [])
        ],
        numero_estudiantes=num_estudiantes,
        clases_restantes=clases_restantes,
    )


@router.get("", response_model=list[FichaResponse])
async def list_fichas(
    archivada: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    current=Depends(get_current_instructor),
):
    repo = SqlAlchemyFichaRepository(db)
    fichas = await repo.find_by_instructor(current["instructor_id"], archivada)
    return [_to_response(f) for f in fichas]


@router.post("", response_model=FichaResponse, status_code=201)
async def create_ficha(
    payload: CreateFichaRequest,
    db: AsyncSession = Depends(get_db),
    current=Depends(get_current_instructor),
):
    repo = SqlAlchemyFichaRepository(db)
    # RN-02 unique
    existing = await repo.find_by_unique(current["instructor_id"], payload.codigo, payload.fecha_inicio)
    if existing:
        raise HTTPException(status_code=409, detail="Ficha ya existe con ese código y fecha")

    # Create ficha
    ficha = FichaModel(
        id=str(uuid.uuid4()),
        instructor_id=current["instructor_id"],
        codigo=payload.codigo,
        nombre=payload.nombre,
        fecha_inicio=payload.fecha_inicio,
        trimestre=(payload.trimestre.strip() if payload.trimestre else trimestre_de(payload.fecha_inicio)),
        total_clases=payload.total_clases,
        nota_minima_aprobacion=payload.nota_minima_aprobacion,
    )
    db.add(ficha)
    await db.flush()

    # Create horarios
    for h in payload.horarios:
        hm = HorarioFichaModel(
            id=str(uuid.uuid4()),
            ficha_id=ficha.id,
            dia_semana=h.dia_semana,
            hora=h.hora,
            duracion_minutos=h.duracion_minutos,
        )
        db.add(hm)
    await db.flush()

    # RN-03 generate clases
    domain_horarios = [DomainHorario(dia_semana=h.dia_semana, hora=h.hora, duracion_minutos=h.duracion_minutos) for h in payload.horarios]
    try:
        clases_gen = ClassScheduleGenerator.generate(payload.fecha_inicio, domain_horarios, payload.total_clases)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    for c in clases_gen:
        cm = ClaseModel(
            id=str(uuid.uuid4()),
            ficha_id=ficha.id,
            fecha=c.fecha,
            hora=c.hora,
            modalidad="PRESENCIAL",
            # Solo el día ya pasado (o hoy) puede nacer realizada
            realizada=(c.fecha <= date.today()),
        )
        db.add(cm)
    await db.flush()
    await db.refresh(ficha, attribute_names=["horarios"])
    return _to_response(ficha)


@router.get("/{ficha_id}", response_model=FichaResponse)
async def get_ficha(ficha_id: str, db: AsyncSession = Depends(get_db), current=Depends(get_current_instructor)):
    repo = SqlAlchemyFichaRepository(db)
    ficha = await repo.find_by_id_and_instructor(ficha_id, current["instructor_id"])
    if not ficha:
        raise HTTPException(status_code=404, detail="Ficha no encontrada")
    return _to_response(ficha)


@router.patch("/{ficha_id}", response_model=FichaResponse)
async def update_ficha(
    ficha_id: str,
    payload: UpdateFichaRequest,
    db: AsyncSession = Depends(get_db),
    current=Depends(get_current_instructor),
):
    repo = SqlAlchemyFichaRepository(db)
    ficha = await repo.find_by_id_and_instructor(ficha_id, current["instructor_id"])
    if not ficha:
        raise HTTPException(status_code=404, detail="Ficha no encontrada")
    # RN-05 read-only if archivada
    if ficha.archivada:
        raise HTTPException(status_code=409, detail="Ficha archivada es de solo lectura")

    # Update fields if provided
    if payload.codigo is not None:
        ficha.codigo = payload.codigo
    if payload.nombre is not None:
        ficha.nombre = payload.nombre
    if payload.fecha_inicio is not None:
        ficha.fecha_inicio = payload.fecha_inicio
    if payload.trimestre is not None:
        ficha.trimestre = payload.trimestre.strip()
    if payload.total_clases is not None:
        ficha.total_clases = payload.total_clases
    if payload.nota_minima_aprobacion is not None:
        ficha.nota_minima_aprobacion = payload.nota_minima_aprobacion

    # Check unique if codigo/fecha changed
    if payload.codigo is not None or payload.fecha_inicio is not None:
        existing = await repo.find_by_unique(ficha.instructor_id, ficha.codigo, ficha.fecha_inicio)
        if existing and existing.id != ficha.id:
            raise HTTPException(status_code=409, detail="Ficha ya existe con ese código y fecha")

    # If horarios or total_clases changed, regenerate future clases without asistencias (RN-06 simplified: regenerate all future)
    if payload.horarios is not None:
        # delete existing horarios
        for h in list(ficha.horarios):
            await db.delete(h)
        await db.flush()
        for h in payload.horarios:
            hm = HorarioFichaModel(
                id=str(uuid.uuid4()), ficha_id=ficha.id, dia_semana=h.dia_semana, hora=h.hora, duracion_minutos=h.duracion_minutos
            )
            db.add(hm)
        await db.flush()

    # For now, not regenerating clases on update to keep simple; Fase 0 spec says regenerar futuras sin asistencia
    await db.flush()
    await db.refresh(ficha, attribute_names=["horarios"])
    return _to_response(ficha)


@router.delete("/{ficha_id}", status_code=204)
async def delete_ficha(ficha_id: str, db: AsyncSession = Depends(get_db), current=Depends(get_current_instructor)):
    repo = SqlAlchemyFichaRepository(db)
    ficha = await repo.find_by_id_and_instructor(ficha_id, current["instructor_id"])
    if not ficha:
        raise HTTPException(status_code=404, detail="Ficha no encontrada")
    # RN-04: no delete if has calificaciones
    act_repo = SqlAlchemyActividadRepository(db)
    has_cal = await act_repo.has_calificaciones_for_ficha(ficha.id)
    if has_cal:
        raise HTTPException(status_code=409, detail="Ficha con calificaciones no se puede eliminar, archívela")
    await repo.delete(ficha)
    return None


@router.post("/{ficha_id}/archive", response_model=FichaResponse)
async def archive_ficha(ficha_id: str, db: AsyncSession = Depends(get_db), current=Depends(get_current_instructor)):
    repo = SqlAlchemyFichaRepository(db)
    ficha = await repo.find_by_id_and_instructor(ficha_id, current["instructor_id"])
    if not ficha:
        raise HTTPException(status_code=404, detail="Ficha no encontrada")
    ficha.archivada = True
    await db.flush()
    await db.refresh(ficha, attribute_names=["horarios"])
    return _to_response(ficha)


@router.post("/{ficha_id}/unarchive", response_model=FichaResponse)
async def unarchive_ficha(ficha_id: str, db: AsyncSession = Depends(get_db), current=Depends(get_current_instructor)):
    repo = SqlAlchemyFichaRepository(db)
    ficha = await repo.find_by_id_and_instructor(ficha_id, current["instructor_id"])
    if not ficha:
        raise HTTPException(status_code=404, detail="Ficha no encontrada")
    ficha.archivada = False
    await db.flush()
    await db.refresh(ficha, attribute_names=["horarios"])
    return _to_response(ficha)


@router.post("/{ficha_id}/finalize", response_model=FichaResponse)
async def finalize_ficha(ficha_id: str, db: AsyncSession = Depends(get_db), current=Depends(get_current_instructor)):
    repo = SqlAlchemyFichaRepository(db)
    ficha = await repo.find_by_id_and_instructor(ficha_id, current["instructor_id"])
    if not ficha:
        raise HTTPException(status_code=404, detail="Ficha no encontrada")
    if ficha.archivada:
        raise HTTPException(status_code=409, detail="Ficha archivada es de solo lectura")
    ficha.finalizada = True
    await db.flush()
    await db.refresh(ficha, attribute_names=["horarios"])
    return _to_response(ficha)


@router.post("/{ficha_id}/reopen", response_model=FichaResponse)
async def reopen_ficha(ficha_id: str, db: AsyncSession = Depends(get_db), current=Depends(get_current_instructor)):
    repo = SqlAlchemyFichaRepository(db)
    ficha = await repo.find_by_id_and_instructor(ficha_id, current["instructor_id"])
    if not ficha:
        raise HTTPException(status_code=404, detail="Ficha no encontrada")
    ficha.finalizada = False
    await db.flush()
    await db.refresh(ficha, attribute_names=["horarios"])
    return _to_response(ficha)
