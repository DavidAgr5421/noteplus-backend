from datetime import date

from app.presentation.http.schemas.base import CamelModel


class AlertaDesercion(CamelModel):
    estudiante_id: str
    nombre: str
    identificacion: str
    tipo_identificacion: str = "CC"
    email: str | None = None
    contacto: str | None = None
    ficha_id: str
    ficha_codigo: str
    ficha_nombre: str
    total_fallas: int
    fallas_injustificadas: int
    total_clases_realizadas: int = 0
    porcentaje_inasistencia: float = 0.0


class DashboardClaseHoy(CamelModel):
    id: str
    ficha_id: str
    ficha_codigo: str
    ficha_nombre: str
    fecha: date
    hora: str | None = None
    modalidad: str
    realizada: bool
    asistencias_registradas: int = 0
    total_estudiantes: int = 0


class DashboardActividadProxima(CamelModel):
    id: str
    ficha_id: str
    ficha_codigo: str
    ficha_nombre: str
    nombre: str
    porcentaje: float
    fecha_limite: date
    dias_restantes: int
    es_subactividad: bool = False


class DashboardFichaResumen(CamelModel):
    id: str
    codigo: str
    nombre: str
    trimestre: str | None = None
    activa: bool = True
    total_estudiantes: int = 0
    total_clases: int = 0
    clases_realizadas: int = 0
    clases_restantes: int = 0
    horario_resumen: str | None = None
    estudiantes_en_riesgo: int = 0


class DashboardKpis(CamelModel):
    total_fichas_activas: int
    total_estudiantes: int
    clases_hoy: int
    clases_hoy_pendientes: int
    estudiantes_en_riesgo: int


class DashboardResponse(CamelModel):
    instructor_nombre: str
    fecha_actual: str
    kpis: DashboardKpis
    clases_hoy: list[DashboardClaseHoy]
    alertas_desercion: list[AlertaDesercion]
    actividades_proximas: list[DashboardActividadProxima]
    fichas: list[DashboardFichaResumen]
