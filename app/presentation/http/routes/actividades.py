from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from app.presentation.http.dependencies import get_db, get_current_instructor
from app.presentation.http.schemas.actividad import (
    CreateActividadRequest,
    UpdateActividadRequest,
    ActividadResponse,
    SaveCalificacionesRequest,
)
from app.infrastructure.persistence.repositories.ficha_repository import SqlAlchemyFichaRepository
from app.infrastructure.persistence.repositories.actividad_repository import SqlAlchemyActividadRepository
from app.infrastructure.persistence.models.actividad_model import ActividadModel

router = APIRouter(tags=["actividades"])


async def _check_ficha(ficha_id: str, instructor_id: str, db: AsyncSession):
    repo = SqlAlchemyFichaRepository(db)
    ficha = await repo.find_by_id_and_instructor(ficha_id, instructor_id)
    if not ficha:
        raise HTTPException(status_code=404, detail="Ficha no encontrada")
    return ficha


def _to_resp(a: ActividadModel, nota_promedio: float | None = None) -> ActividadResponse:
    return ActividadResponse(
        id=a.id,
        ficha_id=a.ficha_id,
        parent_id=a.parent_id,
        nombre=a.nombre,
        porcentaje=float(a.porcentaje),
        fecha_limite=a.fecha_limite,
        orden=a.orden,
        nota_promedio=nota_promedio,
    )


def _promedios_redondeados(
    actividades: list[ActividadModel], califs
) -> dict[str, float | None]:
    """Promedio por actividad a 1 decimal (RN-18 half-up). None si no hay notas."""
    from app.domain.services.grade_calculator import GradeCalculator, ActividadNode, round_half_up

    notas_por_actividad: dict[str, list[float]] = {}
    for c in califs:
        notas_por_actividad.setdefault(c.actividad_id, []).append(float(c.nota))
    nodes = [ActividadNode(id=a.id, porcentaje=float(a.porcentaje), parent_id=a.parent_id) for a in actividades]
    raw = GradeCalculator.promedios_por_actividad(nodes, notas_por_actividad)
    return {aid: (round_half_up(v, 1) if v is not None else None) for aid, v in raw.items()}


def _validate_weights(actividades: list[ActividadModel], new_or_updated: ActividadModel | None = None):
    # RN-12: durante creación permitimos suma <=100 para flujo incremental; solo error si >100.
    # La validación estricta ==100 se aplica al calcular notas.
    from collections import defaultdict

    groups: dict[str, list[float]] = defaultdict(list)
    for act in actividades:
        key = act.parent_id or "__root__"
        pct = float(act.porcentaje)
        if new_or_updated and act.id == new_or_updated.id:
            pct = float(new_or_updated.porcentaje)
        groups[key].append(pct)
    if new_or_updated and new_or_updated.id not in [a.id for a in actividades]:
        key = new_or_updated.parent_id or "__root__"
        groups[key].append(float(new_or_updated.porcentaje))

    for key, pcts in groups.items():
        s = sum(pcts)
        if s - 100 > 0.01:
            raise HTTPException(status_code=400, detail=f"Los porcentajes hermanos no pueden exceder 100 (actual: {s}) en grupo {key}")


@router.get("/fichas/{ficha_id}/actividades", response_model=list[ActividadResponse])
async def list_actividades(ficha_id: str, db: AsyncSession = Depends(get_db), current=Depends(get_current_instructor)):
    await _check_ficha(ficha_id, current["instructor_id"], db)
    repo = SqlAlchemyActividadRepository(db)
    acts = await repo.find_by_ficha(ficha_id)
    califs = await repo.find_calificaciones_by_ficha(ficha_id)
    proms = _promedios_redondeados(acts, califs)
    return [_to_resp(a, proms.get(a.id)) for a in acts]


@router.post("/fichas/{ficha_id}/actividades", response_model=ActividadResponse, status_code=201)
async def create_actividad(ficha_id: str, payload: CreateActividadRequest, db: AsyncSession = Depends(get_db), current=Depends(get_current_instructor)):
    ficha = await _check_ficha(ficha_id, current["instructor_id"], db)
    if ficha.archivada:
        raise HTTPException(status_code=409, detail="Ficha archivada es de solo lectura")
    if ficha.finalizada:
        raise HTTPException(status_code=409, detail="Ficha finalizada, no se pueden modificar actividades")

    # RN-13 depth 2
    if payload.parent_id:
        repo = SqlAlchemyActividadRepository(db)
        parent = await repo.find_by_id(payload.parent_id)
        if not parent or parent.ficha_id != ficha_id:
            raise HTTPException(status_code=404, detail="Actividad padre no encontrada")
        if parent.parent_id is not None:
            raise HTTPException(status_code=400, detail="Profundidad máxima 2 niveles")
    repo = SqlAlchemyActividadRepository(db)
    existing = await repo.find_by_ficha(ficha_id)
    # temporary model for validation
    tmp = ActividadModel(
        id="tmp",
        ficha_id=ficha_id,
        parent_id=payload.parent_id,
        nombre=payload.nombre,
        porcentaje=payload.porcentaje,
        orden=payload.orden,
    )
    _validate_weights(existing, tmp)

    model = ActividadModel(
        id=str(uuid.uuid4()),
        ficha_id=ficha_id,
        parent_id=payload.parent_id,
        nombre=payload.nombre,
        porcentaje=payload.porcentaje,
        fecha_limite=payload.fecha_limite,
        orden=payload.orden,
    )
    await repo.save(model)
    return _to_resp(model)


@router.patch("/fichas/{ficha_id}/actividades/{actividad_id}", response_model=ActividadResponse)
async def update_actividad(ficha_id: str, actividad_id: str, payload: UpdateActividadRequest, db: AsyncSession = Depends(get_db), current=Depends(get_current_instructor)):
    ficha = await _check_ficha(ficha_id, current["instructor_id"], db)
    if ficha.archivada or ficha.finalizada:
        raise HTTPException(status_code=409, detail="Ficha bloqueada, no se pueden modificar actividades")
    repo = SqlAlchemyActividadRepository(db)
    act = await repo.find_by_id(actividad_id)
    if not act or act.ficha_id != ficha_id:
        raise HTTPException(status_code=404, detail="Actividad no encontrada")
    if payload.nombre is not None:
        act.nombre = payload.nombre
    if payload.porcentaje is not None:
        # need to validate weights after change
        existing = await repo.find_by_ficha(ficha_id)
        old_pct = float(act.porcentaje)
        act.porcentaje = payload.porcentaje
        try:
            _validate_weights(existing, act)
        except HTTPException:
            act.porcentaje = old_pct
            raise
    if payload.fecha_limite is not None:
        act.fecha_limite = payload.fecha_limite
    if payload.orden is not None:
        act.orden = payload.orden
    await repo.save(act)
    existing = await repo.find_by_ficha(ficha_id)
    califs = await repo.find_calificaciones_by_ficha(ficha_id)
    proms = _promedios_redondeados(existing, califs)
    return _to_resp(act, proms.get(act.id))


@router.delete("/fichas/{ficha_id}/actividades/{actividad_id}", status_code=204)
async def delete_actividad(ficha_id: str, actividad_id: str, db: AsyncSession = Depends(get_db), current=Depends(get_current_instructor)):
    ficha = await _check_ficha(ficha_id, current["instructor_id"], db)
    if ficha.archivada or ficha.finalizada:
        raise HTTPException(status_code=409, detail="Ficha bloqueada")
    repo = SqlAlchemyActividadRepository(db)
    act = await repo.find_by_id(actividad_id)
    if not act or act.ficha_id != ficha_id:
        raise HTTPException(status_code=404, detail="Actividad no encontrada")
    # Check if has children — if so, delete cascades but we should allow
    await repo.delete(act)
    return None


# Calificaciones
@router.put("/actividades/{actividad_id}/calificaciones", response_model=list[dict])
async def save_calificaciones(actividad_id: str, payload: SaveCalificacionesRequest, db: AsyncSession = Depends(get_db), current=Depends(get_current_instructor)):
    repo = SqlAlchemyActividadRepository(db)
    actividad = await repo.find_by_id(actividad_id)
    if not actividad:
        raise HTTPException(status_code=404, detail="Actividad no encontrada")
    ficha = await _check_ficha(actividad.ficha_id, current["instructor_id"], db)
    if ficha.archivada or ficha.finalizada:
        raise HTTPException(status_code=409, detail="Ficha bloqueada, no se pueden modificar calificaciones")
    # RN-14: only leaf can receive grade
    children = await repo.find_children(actividad_id)
    if children:
        raise HTTPException(status_code=400, detail="Actividad con subactividades no recibe nota directa")
    # Validate estudiantes belong to ficha
    from app.infrastructure.persistence.models.estudiante_model import EstudianteModel

    results = []
    for item in payload.calificaciones:
        est = await db.get(EstudianteModel, item.estudiante_id)
        if not est or est.ficha_id != ficha.id:
            raise HTTPException(status_code=404, detail=f"Estudiante {item.estudiante_id} no encontrado en la ficha")
        model = await repo.upsert_calificacion(actividad_id, item.estudiante_id, item.nota)
        results.append({"actividadId": actividad_id, "estudianteId": item.estudiante_id, "nota": float(model.nota)})
    return results


@router.get("/fichas/{ficha_id}/notas")
async def get_notas(ficha_id: str, db: AsyncSession = Depends(get_db), current=Depends(get_current_instructor)):
    ficha = await _check_ficha(ficha_id, current["instructor_id"], db)
    repo = SqlAlchemyActividadRepository(db)
    actividades = await repo.find_by_ficha(ficha_id)
    # fetch estudiantes
    from app.infrastructure.persistence.models.estudiante_model import EstudianteModel
    from sqlalchemy import select

    result = await db.execute(select(EstudianteModel).where(EstudianteModel.ficha_id == ficha_id).order_by(EstudianteModel.nombre))
    estudiantes = list(result.scalars().all())
    califs = await repo.find_calificaciones_by_ficha(ficha_id)

    # Build grade calculation per estudiante
    from app.domain.services.grade_calculator import GradeCalculator, ActividadNode, CalificacionInput

    nodes = [ActividadNode(id=a.id, porcentaje=float(a.porcentaje), parent_id=a.parent_id) for a in actividades]
    # Validate pesos but not fail — just for info? We will not block
    proms = _promedios_redondeados(actividades, califs)
    acts_resp = [_to_resp(a, proms.get(a.id)) for a in actividades]
    # Map actividad id -> calificacion nota for actividades map (frontend table)
    notas = []
    estudiantes_front = []
    for est in estudiantes:
        est_califs = [c for c in califs if c.estudiante_id == est.id]
        inputs = [CalificacionInput(actividad_id=c.actividad_id, nota=float(c.nota)) for c in est_califs]
        calif_map = {c.actividad_id: float(c.nota) for c in est_califs}
        if nodes:
            calc = GradeCalculator.calculate(nodes, inputs, float(ficha.nota_minima_aprobacion))
            detalle = [{"actividadId": d.actividad_id, "notaEfectiva": d.nota_efectiva, "porcentaje": d.porcentaje} for d in calc.detalle]
            notas.append(
                {
                    "estudianteId": est.id,
                    "estudianteNombre": est.nombre,
                    "identificacion": est.identificacion,
                    "notaFinal": calc.nota_final,
                    "notaAcumulada": calc.nota_acumulada,
                    "estado": calc.estado,
                    "detalle": detalle,
                }
            )
            # Frontend NotasTable shape: actividades as Record<actividadId, nota>
            actividades_map = {c.actividad_id: float(c.nota) for c in est_califs}
            estudiantes_front.append(
                {
                    "estudianteId": est.id,
                    "estudianteNombre": est.nombre,
                    "estudianteIdentificacion": est.identificacion,
                    "notaFinal": calc.nota_final,
                    "notaAcumulada": calc.nota_acumulada if calc.nota_acumulada is not None else 0.0,
                    "estado": calc.estado,
                    "actividades": actividades_map,
                }
            )
        else:
            notas.append(
                {
                    "estudianteId": est.id,
                    "estudianteNombre": est.nombre,
                    "identificacion": est.identificacion,
                    "notaFinal": 0.0,
                    "notaAcumulada": None,
                    "estado": "NO_APROBADO",
                    "detalle": [],
                }
            )
            estudiantes_front.append(
                {
                    "estudianteId": est.id,
                    "estudianteNombre": est.nombre,
                    "estudianteIdentificacion": est.identificacion,
                    "notaFinal": 0.0,
                    "notaAcumulada": 0.0,
                    "estado": "NO_APROBADO",
                    "actividades": {},
                }
            )
    return {
        "fichaId": ficha_id,
        "notaMinimaAprobacion": float(ficha.nota_minima_aprobacion),
        "actividades": [a.model_dump(by_alias=True) for a in acts_resp],
        "notas": notas,
        "estudiantes": estudiantes_front,
    }
