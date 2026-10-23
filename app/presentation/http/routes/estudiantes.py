import csv
import io
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import TypeAdapter
from pydantic import ValidationError as PydanticValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.persistence.models.estudiante_model import EstudianteModel
from app.infrastructure.persistence.repositories.estudiante_repository import (
    SqlAlchemyEstudianteRepository,
)
from app.infrastructure.persistence.repositories.ficha_repository import SqlAlchemyFichaRepository
from app.presentation.http.dependencies import get_current_instructor, get_db
from app.presentation.http.schemas.estudiante import (
    CreateEstudianteRequest,
    EstudianteResponse,
    ImportBatchRequest,
    ImportBatchResponse,
    ImportEstudianteItem,
    UpdateEstudianteRequest,
    validar_tipo_identificacion,
)

router = APIRouter(prefix="/fichas/{ficha_id}/estudiantes", tags=["estudiantes"])


async def _check_ficha(ficha_id: str, instructor_id: str, db: AsyncSession):
    repo = SqlAlchemyFichaRepository(db)
    ficha = await repo.find_by_id_and_instructor(ficha_id, instructor_id)
    if not ficha:
        raise HTTPException(status_code=404, detail="Ficha no encontrada")
    if ficha.archivada:
        raise HTTPException(status_code=409, detail="Ficha archivada es de solo lectura")
    return ficha


def _to_resp(e: EstudianteModel) -> EstudianteResponse:
    return EstudianteResponse(
        id=e.id,
        ficha_id=e.ficha_id,
        nombre=e.nombre,
        identificacion=e.identificacion,
        tipo_identificacion=getattr(e, "tipo_identificacion", None) or "CC",
        email=e.email,
        contacto=getattr(e, "contacto", None),
    )


@router.get("", response_model=list[EstudianteResponse])
async def list_estudiantes(ficha_id: str, db: AsyncSession = Depends(get_db), current=Depends(get_current_instructor)):
    # RN-01 check exists
    repo_f = SqlAlchemyFichaRepository(db)
    ficha = await repo_f.find_by_id_and_instructor(ficha_id, current["instructor_id"])
    if not ficha:
        raise HTTPException(status_code=404, detail="Ficha no encontrada")
    repo = SqlAlchemyEstudianteRepository(db)
    estudiantes = await repo.find_by_ficha(ficha_id)
    return [_to_resp(e) for e in estudiantes]


@router.post("", response_model=EstudianteResponse, status_code=201)
async def create_estudiante(ficha_id: str, payload: CreateEstudianteRequest, db: AsyncSession = Depends(get_db), current=Depends(get_current_instructor)):
    await _check_ficha(ficha_id, current["instructor_id"], db)
    repo = SqlAlchemyEstudianteRepository(db)
    existing = await repo.find_by_ficha_and_identificacion(ficha_id, payload.identificacion)
    if existing:
        raise HTTPException(status_code=409, detail="Identificación ya existe en la ficha")
    model = EstudianteModel(
        id=str(uuid.uuid4()),
        ficha_id=ficha_id,
        nombre=payload.nombre,
        identificacion=payload.identificacion,
        tipo_identificacion=payload.tipo_identificacion,
        email=str(payload.email) if payload.email else None,
        contacto=payload.contacto,
    )
    await repo.save(model)
    return _to_resp(model)


@router.get("/{estudiante_id}", response_model=EstudianteResponse)
async def get_estudiante(ficha_id: str, estudiante_id: str, db: AsyncSession = Depends(get_db), current=Depends(get_current_instructor)):
    repo_f = SqlAlchemyFichaRepository(db)
    ficha = await repo_f.find_by_id_and_instructor(ficha_id, current["instructor_id"])
    if not ficha:
        raise HTTPException(status_code=404, detail="Ficha no encontrada")
    repo = SqlAlchemyEstudianteRepository(db)
    est = await repo.find_by_id(estudiante_id)
    if not est or est.ficha_id != ficha_id:
        raise HTTPException(status_code=404, detail="Estudiante no encontrado")
    return _to_resp(est)


@router.post("/import", response_model=dict, deprecated=True)
async def import_estudiantes(ficha_id: str, file: UploadFile = File(...), db: AsyncSession = Depends(get_db), current=Depends(get_current_instructor)):
    """LEGACY: importar desde CSV rígido. Preferir POST /import-batch con JSON normalizado."""
    await _check_ficha(ficha_id, current["instructor_id"], db)
    content = await file.read()
    try:
        text = content.decode("utf-8-sig")
    except Exception:
        raise HTTPException(status_code=400, detail="Archivo inválido, se espera CSV UTF-8")
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames or "nombre" not in reader.fieldnames or "identificacion" not in reader.fieldnames:
        raise HTTPException(status_code=400, detail="CSV debe tener columnas nombre,identificacion[,tipo_identificacion,email,contacto]")
    repo = SqlAlchemyEstudianteRepository(db)
    imported = 0
    errors: list[str] = []
    for i, row in enumerate(reader, start=2):
        nombre = (row.get("nombre") or "").strip()
        identificacion = (row.get("identificacion") or "").strip()
        email = (row.get("email") or "").strip() or None
        contacto = (row.get("contacto") or "").strip() or None
        if not nombre or not identificacion:
            errors.append(f"Fila {i}: nombre e identificacion requeridos")
            continue
        try:
            tipo = validar_tipo_identificacion(row.get("tipo_identificacion"))
        except ValueError as e:
            errors.append(f"Fila {i}: {e}")
            continue
        existing = await repo.find_by_ficha_and_identificacion(ficha_id, identificacion)
        if existing:
            errors.append(f"Fila {i}: identificación {identificacion} ya existe")
            continue
        model = EstudianteModel(
            id=str(uuid.uuid4()), ficha_id=ficha_id, nombre=nombre, identificacion=identificacion,
            tipo_identificacion=tipo, email=email, contacto=contacto
        )
        await repo.save(model)
        imported += 1
    return {"imported": imported, "errors": errors}


@router.post("/import-batch", response_model=ImportBatchResponse, status_code=201)
async def import_estudiantes_batch(
    ficha_id: str,
    payload: ImportBatchRequest,
    db: AsyncSession = Depends(get_db),
    current=Depends(get_current_instructor),
):
    """Importar lote ya normalizado por el frontend (RN-07: identificación única por ficha)."""
    await _check_ficha(ficha_id, current["instructor_id"], db)
    if len(payload.estudiantes) > 1000:
        raise HTTPException(status_code=400, detail="Máximo 1000 estudiantes por lote")
    repo = SqlAlchemyEstudianteRepository(db)
    created = 0
    skipped: list[dict] = []
    seen: set[str] = set()
    adapter = TypeAdapter(ImportEstudianteItem)
    for i, raw in enumerate(payload.estudiantes):
        try:
            item = adapter.validate_python(raw)
        except PydanticValidationError as e:
            reasons = "; ".join(err.get("msg", "dato inválido") for err in e.errors(include_url=False))
            skipped.append({"index": i, "reason": f"fila {i + 1}: {reasons}"})
            continue
        email = (item.email or "").strip() or None
        contacto = (item.contacto or "").strip() or None
        if item.identificacion in seen:
            skipped.append({"index": i, "reason": f"identificación {item.identificacion} duplicada en el lote"})
            continue
        seen.add(item.identificacion)
        existing = await repo.find_by_ficha_and_identificacion(ficha_id, item.identificacion)
        if existing:
            skipped.append({"index": i, "reason": f"identificación {item.identificacion} ya existe en la ficha"})
            continue
        model = EstudianteModel(
            id=str(uuid.uuid4()),
            ficha_id=ficha_id,
            nombre=item.nombre,
            identificacion=item.identificacion,
            tipo_identificacion=item.tipo_identificacion,
            email=email,
            contacto=contacto,
        )
        await repo.save(model)
        created += 1
    return ImportBatchResponse(created=created, skipped=skipped)  # type: ignore[arg-type]


@router.patch("/{estudiante_id}", response_model=EstudianteResponse)
async def update_estudiante(ficha_id: str, estudiante_id: str, payload: UpdateEstudianteRequest, db: AsyncSession = Depends(get_db), current=Depends(get_current_instructor)):
    await _check_ficha(ficha_id, current["instructor_id"], db)
    repo = SqlAlchemyEstudianteRepository(db)
    est = await repo.find_by_id(estudiante_id)
    if not est or est.ficha_id != ficha_id:
        raise HTTPException(status_code=404, detail="Estudiante no encontrado")
    if payload.identificacion and payload.identificacion != est.identificacion:
        existing = await repo.find_by_ficha_and_identificacion(ficha_id, payload.identificacion)
        if existing:
            raise HTTPException(status_code=409, detail="Identificación ya existe")
        est.identificacion = payload.identificacion
    if payload.nombre is not None:
        est.nombre = payload.nombre
    if payload.tipo_identificacion is not None:
        est.tipo_identificacion = payload.tipo_identificacion
    if payload.email is not None:
        est.email = str(payload.email) if payload.email else None
    if payload.contacto is not None:
        est.contacto = payload.contacto.strip() or None
    # also handle clearing email to None via empty
    await repo.save(est)
    return _to_resp(est)


@router.delete("/{estudiante_id}", status_code=204)
async def delete_estudiante(ficha_id: str, estudiante_id: str, db: AsyncSession = Depends(get_db), current=Depends(get_current_instructor)):
    await _check_ficha(ficha_id, current["instructor_id"], db)
    repo = SqlAlchemyEstudianteRepository(db)
    est = await repo.find_by_id(estudiante_id)
    if not est or est.ficha_id != ficha_id:
        raise HTTPException(status_code=404, detail="Estudiante no encontrado")
    await repo.delete(est)
    return None
