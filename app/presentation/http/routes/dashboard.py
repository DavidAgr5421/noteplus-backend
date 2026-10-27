from datetime import datetime, timedelta
import pytz
from fastapi import APIRouter, Depends
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.infrastructure.persistence.models.actividad_model import ActividadModel
from app.infrastructure.persistence.models.asistencia_model import AsistenciaModel
from app.infrastructure.persistence.models.clase_model import ClaseModel
from app.infrastructure.persistence.models.estudiante_model import EstudianteModel
from app.infrastructure.persistence.models.ficha_model import FichaModel
from app.infrastructure.persistence.models.instructor_model import InstructorModel
from app.presentation.http.dependencies import get_current_instructor, get_db
from app.presentation.http.schemas.dashboard import (
    AlertaDesercion,
    DashboardActividadProxima,
    DashboardClaseHoy,
    DashboardFichaResumen,
    DashboardKpis,
    DashboardResponse,
)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])
TZ = pytz.timezone("America/Bogota")
DIAS_ABREV = {0: "Lun", 1: "Mar", 2: "Mié", 3: "Jue", 4: "Vie", 5: "Sáb", 6: "Dom"}


def _formatear_horario_resumen(horarios: list) -> str:
    if not horarios:
        return "Sin horario"
    sorted_h = sorted(horarios, key=lambda h: (h.dia_semana, h.hora))
    partes = [f"{DIAS_ABREV.get(h.dia_semana, '')} {h.hora[:5]}".strip() for h in sorted_h]
    if len(partes) > 2:
        return f"{' · '.join(partes[:2])} +{len(partes) - 2}"
    return " · ".join(partes)


@router.get("", response_model=DashboardResponse)
async def get_dashboard(
    db: AsyncSession = Depends(get_db),
    current=Depends(get_current_instructor),
):
    instructor_id = current["instructor_id"]
    now = datetime.now(TZ)
    today = now.date()

    # 1. Instructor
    inst_res = await db.execute(select(InstructorModel).where(InstructorModel.id == instructor_id))
    instructor = inst_res.scalar_one_or_none()
    instructor_nombre = instructor.nombre if instructor else "Instructor"

    # 2. Fichas del instructor
    fichas_res = await db.execute(
        select(FichaModel)
        .options(selectinload(FichaModel.horarios))
        .where(FichaModel.instructor_id == instructor_id, FichaModel.archivada == False)  # noqa: E712
        .order_by(FichaModel.nombre)
    )
    todas_fichas = fichas_res.scalars().all()
    fichas_activas = [f for f in todas_fichas if not f.finalizada]
    fichas_activas_ids = [f.id for f in fichas_activas]
    fichas_map = {f.id: f for f in todas_fichas}

    # 3. Clases de hoy
    clases_hoy: list[DashboardClaseHoy] = []
    if fichas_activas_ids:
        clases_hoy_res = await db.execute(
            select(ClaseModel)
            .where(ClaseModel.ficha_id.in_(fichas_activas_ids), ClaseModel.fecha == today)
            .order_by(ClaseModel.hora.asc().nulls_last())
        )
        clases_hoy_models = clases_hoy_res.scalars().all()

        for c in clases_hoy_models:
            f = fichas_map.get(c.ficha_id)
            if not f:
                continue

            # Conteo de asistencias tomadas
            asist_count_res = await db.execute(
                select(func.count(AsistenciaModel.id)).where(AsistenciaModel.clase_id == c.id)
            )
            asist_registradas = asist_count_res.scalar() or 0

            # Total estudiantes en la ficha
            est_count_res = await db.execute(
                select(func.count(EstudianteModel.id)).where(EstudianteModel.ficha_id == f.id)
            )
            total_est = est_count_res.scalar() or 0

            clases_hoy.append(
                DashboardClaseHoy(
                    id=c.id,
                    ficha_id=f.id,
                    ficha_codigo=f.codigo,
                    ficha_nombre=f.nombre,
                    fecha=c.fecha,
                    hora=c.hora,
                    modalidad=c.modalidad,
                    realizada=c.realizada,
                    asistencias_registradas=asist_registradas,
                    total_estudiantes=total_est,
                )
            )

    # 4. Total clases realizadas por ficha (para calcular % inasistencia)
    clases_realizadas_por_ficha: dict[str, int] = {}
    total_clases_por_ficha: dict[str, int] = {}
    if fichas_activas_ids:
        clases_stat_res = await db.execute(
            select(
                ClaseModel.ficha_id,
                func.count(ClaseModel.id).label("total"),
                func.sum(case((ClaseModel.realizada == True, 1), else_=0)).label("realizadas"),  # noqa: E712
            )
            .where(ClaseModel.ficha_id.in_(fichas_activas_ids))
            .group_by(ClaseModel.ficha_id)
        )
        for row in clases_stat_res:
            total_clases_por_ficha[row.ficha_id] = int(row.total or 0)
            clases_realizadas_por_ficha[row.ficha_id] = int(row.realizadas or 0)

    # 5. Alertas de deserción (estudiantes con >= 3 fallas acumuladas)
    alertas_desercion: list[AlertaDesercion] = []
    estudiantes_en_riesgo_por_ficha: dict[str, int] = {}

    if fichas_activas_ids:
        stmt_fallas = (
            select(
                EstudianteModel.id,
                EstudianteModel.nombre,
                EstudianteModel.identificacion,
                EstudianteModel.tipo_identificacion,
                EstudianteModel.email,
                EstudianteModel.contacto,
                EstudianteModel.ficha_id,
                func.count(AsistenciaModel.id).label("total_fallas"),
                func.sum(
                    case(
                        (
                            (AsistenciaModel.justificacion.is_(None))
                            | (func.trim(AsistenciaModel.justificacion) == ""),
                            1,
                        ),
                        else_=0,
                    )
                ).label("fallas_injustificadas"),
            )
            .join(AsistenciaModel, AsistenciaModel.estudiante_id == EstudianteModel.id)
            .where(
                EstudianteModel.ficha_id.in_(fichas_activas_ids),
                AsistenciaModel.estado == "NO_ASISTIO",
            )
            .group_by(
                EstudianteModel.id,
                EstudianteModel.nombre,
                EstudianteModel.identificacion,
                EstudianteModel.tipo_identificacion,
                EstudianteModel.email,
                EstudianteModel.contacto,
                EstudianteModel.ficha_id,
            )
            .having(func.count(AsistenciaModel.id) >= 3)
            .order_by(func.count(AsistenciaModel.id).desc())
        )
        res_fallas = await db.execute(stmt_fallas)

        for row in res_fallas:
            f = fichas_map.get(row.ficha_id)
            if not f:
                continue

            clases_realizadas = clases_realizadas_por_ficha.get(row.ficha_id, 0)
            porcentaje = (
                round((row.total_fallas / clases_realizadas) * 100, 1)
                if clases_realizadas > 0
                else 0.0
            )

            estudiantes_en_riesgo_por_ficha[row.ficha_id] = (
                estudiantes_en_riesgo_por_ficha.get(row.ficha_id, 0) + 1
            )

            alertas_desercion.append(
                AlertaDesercion(
                    estudiante_id=row.id,
                    nombre=row.nombre,
                    identificacion=row.identificacion,
                    tipo_identificacion=row.tipo_identificacion or "CC",
                    email=row.email,
                    contacto=row.contacto,
                    ficha_id=f.id,
                    ficha_codigo=f.codigo,
                    ficha_nombre=f.nombre,
                    total_fallas=int(row.total_fallas),
                    fallas_injustificadas=int(row.fallas_injustificadas or 0),
                    total_clases_realizadas=clases_realizadas,
                    porcentaje_inasistencia=porcentaje,
                )
            )

    # 6. Actividades próximas a vencer (próximos 7 días)
    actividades_proximas: list[DashboardActividadProxima] = []
    if fichas_activas_ids:
        limite_proximas = today + timedelta(days=7)
        acts_res = await db.execute(
            select(ActividadModel)
            .where(
                ActividadModel.ficha_id.in_(fichas_activas_ids),
                ActividadModel.fecha_limite >= today,
                ActividadModel.fecha_limite <= limite_proximas,
            )
            .order_by(ActividadModel.fecha_limite.asc())
        )
        for a in acts_res.scalars().all():
            f = fichas_map.get(a.ficha_id)
            if not f or not a.fecha_limite:
                continue
            dias_restantes = (a.fecha_limite - today).days
            actividades_proximas.append(
                DashboardActividadProxima(
                    id=a.id,
                    ficha_id=f.id,
                    ficha_codigo=f.codigo,
                    ficha_nombre=f.nombre,
                    nombre=a.nombre,
                    porcentaje=a.porcentaje,
                    fecha_limite=a.fecha_limite,
                    dias_restantes=dias_restantes,
                    es_subactividad=bool(a.parent_id),
                )
            )

    # 7. Resumen de Fichas Activas
    fichas_resumen: list[DashboardFichaResumen] = []
    total_estudiantes_global = 0

    for f in fichas_activas:
        est_count = await db.execute(
            select(func.count(EstudianteModel.id)).where(EstudianteModel.ficha_id == f.id)
        )
        count_est = est_count.scalar() or 0
        total_estudiantes_global += count_est

        total_c = f.total_clases or total_clases_por_ficha.get(f.id, 0)
        realizadas_c = clases_realizadas_por_ficha.get(f.id, 0)
        clases_rest = max(0, total_c - realizadas_c)

        trimestre_str = str(f.trimestre).strip() if f.trimestre else None
        if not trimestre_str and f.fecha_inicio:
            trimestre_str = f"T{(f.fecha_inicio.month - 1) // 3 + 1} {f.fecha_inicio.year}"

        fichas_resumen.append(
            DashboardFichaResumen(
                id=f.id,
                codigo=f.codigo,
                nombre=f.nombre,
                trimestre=trimestre_str,
                activa=not f.finalizada and not f.archivada,
                total_estudiantes=count_est,
                total_clases=total_c,
                clases_realizadas=realizadas_c,
                clases_restantes=clases_rest,
                horario_resumen=_formatear_horario_resumen(f.horarios),
                estudiantes_en_riesgo=estudiantes_en_riesgo_por_ficha.get(f.id, 0),
            )
        )

    # 8. KPIs globales
    clases_pendientes_hoy = len([c for c in clases_hoy if not c.realizada])
    kpis = DashboardKpis(
        total_fichas_activas=len(fichas_activas),
        total_estudiantes=total_estudiantes_global,
        clases_hoy=len(clases_hoy),
        clases_hoy_pendientes=clases_pendientes_hoy,
        estudiantes_en_riesgo=len([a for a in alertas_desercion if a.total_fallas > 3]),
    )

    dias_semana = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
    meses = [
        "enero", "febrero", "marzo", "abril", "mayo", "junio",
        "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"
    ]
    fecha_formateada = f"{dias_semana[today.weekday()]}, {today.day} de {meses[today.month - 1]} de {today.year}"

    return DashboardResponse(
        instructor_nombre=instructor_nombre,
        fecha_actual=fecha_formateada,
        kpis=kpis,
        clases_hoy=clases_hoy,
        alertas_desercion=alertas_desercion,
        actividades_proximas=actividades_proximas,
        fichas=fichas_resumen,
    )
