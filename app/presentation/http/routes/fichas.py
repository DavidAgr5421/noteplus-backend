import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.errors import ConflictError
from app.domain.services.class_schedule_generator import ClassScheduleGenerator
from app.domain.services.class_schedule_generator import HorarioInput as DomainHorario
from app.infrastructure.persistence.models.clase_model import ClaseModel
from app.infrastructure.persistence.models.ficha_model import FichaModel
from app.infrastructure.persistence.models.horario_ficha_model import HorarioFichaModel
from app.infrastructure.persistence.repositories.actividad_repository import (
    SqlAlchemyActividadRepository,
)
from app.infrastructure.persistence.repositories.ficha_repository import SqlAlchemyFichaRepository
from app.presentation.http.dependencies import get_current_instructor, get_db
from app.presentation.http.schemas.ficha import (
    CreateFichaRequest,
    FichaResponse,
    HorarioInput,
    UpdateFichaRequest,
)

router = APIRouter(prefix="/fichas", tags=["fichas"])

DIAS_SEMANA_NOMBRES = {
    0: "Domingo",
    1: "Lunes",
    2: "Martes",
    3: "Miércoles",
    4: "Jueves",
    5: "Viernes",
    6: "Sábado",
}


def _hora_a_minutos(hora: str) -> int:
    partes = (hora or "00:00")[:5].split(":")
    return int(partes[0]) * 60 + int(partes[1])


def _minutos_a_hora(minutos: int) -> str:
    h = (minutos // 60) % 24
    m = minutos % 60
    return f"{h:02d}:{m:02d}"


async def _verificar_solapamiento_horarios(
    repo: SqlAlchemyFichaRepository,
    instructor_id: str,
    horarios_propuestos: list[HorarioInput],
    exclude_ficha_id: str | None = None,
    accion: str = "crear",
) -> None:
    if not horarios_propuestos:
        return

    conflicts: list[dict] = []

    # 1. Solapamiento dentro de la misma ficha
    for i in range(len(horarios_propuestos)):
        ha = horarios_propuestos[i]
        start_a = _hora_a_minutos(ha.hora)
        end_a = start_a + ha.duracion_minutos
        for j in range(i + 1, len(horarios_propuestos)):
            hb = horarios_propuestos[j]
            if ha.dia_semana != hb.dia_semana:
                continue
            start_b = _hora_a_minutos(hb.hora)
            end_b = start_b + hb.duracion_minutos
            if start_a < end_b and start_b < end_a:
                dia_nombre = DIAS_SEMANA_NOMBRES.get(ha.dia_semana, f"Día {ha.dia_semana}")
                conflicts.append(
                    {
                        "fichaId": exclude_ficha_id or "",
                        "fichaNombre": "Esta misma ficha",
                        "fichaCodigo": "Horario interno",
                        "diaSemana": ha.dia_semana,
                        "diaNombre": dia_nombre,
                        "horaExistenteInicio": _minutos_a_hora(start_a),
                        "horaExistenteFin": _minutos_a_hora(end_a),
                        "horaPropuestaInicio": _minutos_a_hora(start_b),
                        "horaPropuestaFin": _minutos_a_hora(end_b),
                        "isSameFicha": True,
                    }
                )

    # 2. Solapamiento con otras fichas activas del instructor
    fichas_activas = await repo.find_by_instructor(instructor_id, archivada=False)
    for otra_ficha in fichas_activas:
        if exclude_ficha_id and otra_ficha.id == exclude_ficha_id:
            continue
        if otra_ficha.finalizada:
            continue
        otros_horarios = otra_ficha.__dict__.get("horarios") or []
        for hp in horarios_propuestos:
            start_p = _hora_a_minutos(hp.hora)
            end_p = start_p + hp.duracion_minutos
            for he in otros_horarios:
                if hp.dia_semana != he.dia_semana:
                    continue
                start_e = _hora_a_minutos(he.hora)
                end_e = start_e + he.duracion_minutos
                if start_p < end_e and start_e < end_p:
                    dia_nombre = DIAS_SEMANA_NOMBRES.get(hp.dia_semana, f"Día {hp.dia_semana}")
                    conflicts.append(
                        {
                            "fichaId": otra_ficha.id,
                            "fichaNombre": otra_ficha.nombre,
                            "fichaCodigo": otra_ficha.codigo,
                            "diaSemana": hp.dia_semana,
                            "diaNombre": dia_nombre,
                            "horaExistenteInicio": _minutos_a_hora(start_e),
                            "horaExistenteFin": _minutos_a_hora(end_e),
                            "horaPropuestaInicio": _minutos_a_hora(start_p),
                            "horaPropuestaFin": _minutos_a_hora(end_p),
                            "isSameFicha": False,
                        }
                    )

    if conflicts:
        first = conflicts[0]
        verbo = "crear la ficha" if accion == "crear" else "modificar el horario"
        if first.get("isSameFicha"):
            msg = (
                f"No se puede {verbo} porque dos horarios de la misma ficha se solapan el día "
                f"{first['diaNombre']} ({first['horaExistenteInicio']} - {first['horaExistenteFin']} "
                f"con {first['horaPropuestaInicio']} - {first['horaPropuestaFin']})."
            )
        else:
            msg = (
                f"No se puede {verbo} porque el horario se solapa con la ficha "
                f"\"{first['fichaNombre']}\" (Código: {first['fichaCodigo']}) el día {first['diaNombre']} "
                f"de {first['horaExistenteInicio']} a {first['horaExistenteFin']} "
                f"(horario propuesto: {first['horaPropuestaInicio']} a {first['horaPropuestaFin']})."
            )
        raise ConflictError(message=msg, details={"conflicts": conflicts, "accion": accion})


def trimestre_de(fecha: date) -> str:
    """Trimestre calendario T1–T4 + año, derivado de la fecha de inicio."""
    return f"T{(fecha.month - 1) // 3 + 1} {fecha.year}"


def _to_response(ficha: FichaModel) -> FichaResponse:
    # Nota: usar __dict__ para no disparar lazy-load en sesión async
    # (MissingGreenlet si estudiantes/clases no fueron cargados con selectinload).
    est = ficha.__dict__.get("estudiantes")
    num_estudiantes = len(est) if est is not None else 0
    cls = ficha.__dict__.get("clases")
    if cls is not None and len(cls) > 0:
        clases_restantes = sum(1 for c in cls if not c.realizada)
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
            for h in (ficha.__dict__.get("horarios") or [])
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

    # Validar solapamiento de horarios con otras fichas activas
    await _verificar_solapamiento_horarios(
        repo=repo,
        instructor_id=current["instructor_id"],
        horarios_propuestos=payload.horarios,
        exclude_ficha_id=None,
        accion="crear",
    )

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
    # Re-fetch con selectinload para conteos correctos (evita lazy-load async)
    fresh = await repo.find_by_id_and_instructor(ficha.id, current["instructor_id"])
    return _to_response(fresh if fresh is not None else ficha)


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

    # Validar solapamiento de horarios antes de modificar
    if payload.horarios is not None:
        await _verificar_solapamiento_horarios(
            repo=repo,
            instructor_id=current["instructor_id"],
            horarios_propuestos=payload.horarios,
            exclude_ficha_id=ficha.id,
            accion="modificar",
        )

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
    db.expire(ficha)
    fresh = await repo.find_by_id_and_instructor(ficha_id, current["instructor_id"])
    return _to_response(fresh if fresh is not None else ficha)


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
    db.expire(ficha)
    fresh = await repo.find_by_id_and_instructor(ficha_id, current["instructor_id"])
    return _to_response(fresh if fresh is not None else ficha)


@router.post("/{ficha_id}/unarchive", response_model=FichaResponse)
async def unarchive_ficha(ficha_id: str, db: AsyncSession = Depends(get_db), current=Depends(get_current_instructor)):
    repo = SqlAlchemyFichaRepository(db)
    ficha = await repo.find_by_id_and_instructor(ficha_id, current["instructor_id"])
    if not ficha:
        raise HTTPException(status_code=404, detail="Ficha no encontrada")
    ficha.archivada = False
    await db.flush()
    db.expire(ficha)
    fresh = await repo.find_by_id_and_instructor(ficha_id, current["instructor_id"])
    return _to_response(fresh if fresh is not None else ficha)


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
    db.expire(ficha)
    fresh = await repo.find_by_id_and_instructor(ficha_id, current["instructor_id"])
    return _to_response(fresh if fresh is not None else ficha)


@router.post("/{ficha_id}/reopen", response_model=FichaResponse)
async def reopen_ficha(ficha_id: str, db: AsyncSession = Depends(get_db), current=Depends(get_current_instructor)):
    repo = SqlAlchemyFichaRepository(db)
    ficha = await repo.find_by_id_and_instructor(ficha_id, current["instructor_id"])
    if not ficha:
        raise HTTPException(status_code=404, detail="Ficha no encontrada")
    ficha.finalizada = False
    await db.flush()
    db.expire(ficha)
    fresh = await repo.find_by_id_and_instructor(ficha_id, current["instructor_id"])
    return _to_response(fresh if fresh is not None else ficha)
