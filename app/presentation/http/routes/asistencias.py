from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.persistence.models.clase_model import ClaseModel
from app.infrastructure.persistence.models.estudiante_model import EstudianteModel
from app.infrastructure.persistence.repositories.asistencia_repository import (
    SqlAlchemyAsistenciaRepository,
)
from app.infrastructure.persistence.repositories.ficha_repository import SqlAlchemyFichaRepository
from app.presentation.http.dependencies import get_current_instructor, get_db
from app.presentation.http.schemas.asistencia import AsistenciaResponse, SaveAsistenciasRequest

router = APIRouter(prefix="/clases", tags=["asistencias"])


async def _get_clase_checked(clase_id: str, instructor_id: str, db: AsyncSession):
    clase = await db.get(ClaseModel, clase_id)
    if not clase:
        raise HTTPException(status_code=404, detail="Clase no encontrada")
    ficha_repo = SqlAlchemyFichaRepository(db)
    ficha = await ficha_repo.find_by_id_and_instructor(clase.ficha_id, instructor_id)
    if not ficha:
        raise HTTPException(status_code=404, detail="Clase no encontrada")
    if ficha.archivada:
        raise HTTPException(status_code=409, detail="Ficha archivada es de solo lectura")
    return clase, ficha


@router.get("/{clase_id}/asistencias", response_model=list[AsistenciaResponse])
async def get_asistencias(clase_id: str, db: AsyncSession = Depends(get_db), current=Depends(get_current_instructor)):
    clase, _ = await _get_clase_checked(clase_id, current["instructor_id"], db)
    repo = SqlAlchemyAsistenciaRepository(db)
    asistencias = await repo.find_by_clase(clase.id)
    # enrich with estudiante name
    if asistencias:
        est_ids = [a.estudiante_id for a in asistencias]
        result = await db.execute(select(EstudianteModel).where(EstudianteModel.id.in_(est_ids)))
        est_map = {e.id: e for e in result.scalars().all()}
    else:
        est_map = {}
    return [
        AsistenciaResponse(
            id=a.id,
            clase_id=a.clase_id,
            estudiante_id=a.estudiante_id,
            estudiante_nombre=est_map.get(a.estudiante_id).nombre if est_map.get(a.estudiante_id) else None,
            estado=a.estado,
            justificacion=a.justificacion,
        )
        for a in asistencias
    ]


@router.put("/{clase_id}/asistencias", response_model=list[AsistenciaResponse])
async def save_asistencias(clase_id: str, payload: SaveAsistenciasRequest, db: AsyncSession = Depends(get_db), current=Depends(get_current_instructor)):
    clase, ficha = await _get_clase_checked(clase_id, current["instructor_id"], db)
    # RN-09: las asistencias se pueden registrar/modificar aunque la clase
    # no esté marcada como realizada (`realizada` es estado informativo).
    # RN-11 asistencias editable even if finalizada — only ficha archivada blocked above
    # Update observacion if provided
    if payload.observacion is not None:
        clase.observacion = payload.observacion
        await db.flush()

    # Validate estudiantes belong to same ficha
    repo = SqlAlchemyAsistenciaRepository(db)
    result_list = []
    for item in payload.asistencias:
        est = await db.get(EstudianteModel, item.estudiante_id)
        if not est or est.ficha_id != ficha.id:
            raise HTTPException(status_code=404, detail=f"Estudiante {item.estudiante_id} no encontrado en la ficha")
        model = await repo.upsert(clase.id, item.estudiante_id, item.estado, item.justificacion)
        result_list.append(model)

    # La clase queda marcada como realizada si ya es su fecha (o pasó).
    # Si es futura, queda como está y el front pregunta al docente si marcarla.
    if clase.fecha <= date.today() and not clase.realizada:
        clase.realizada = True
    await db.flush()

    # enrich names
    if result_list:
        est_ids = [a.estudiante_id for a in result_list]
        result = await db.execute(select(EstudianteModel).where(EstudianteModel.id.in_(est_ids)))
        est_map = {e.id: e for e in result.scalars().all()}
    else:
        est_map = {}
    return [
        AsistenciaResponse(
            id=a.id,
            clase_id=a.clase_id,
            estudiante_id=a.estudiante_id,
            estudiante_nombre=est_map.get(a.estudiante_id).nombre if est_map.get(a.estudiante_id) else None,
            estado=a.estado,
            justificacion=a.justificacion,
        )
        for a in result_list
    ]
