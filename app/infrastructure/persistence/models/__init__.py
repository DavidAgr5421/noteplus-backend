from app.infrastructure.persistence.models.actividad_model import ActividadModel
from app.infrastructure.persistence.models.asistencia_model import AsistenciaModel
from app.infrastructure.persistence.models.calificacion_model import CalificacionModel
from app.infrastructure.persistence.models.clase_model import ClaseModel
from app.infrastructure.persistence.models.estudiante_model import EstudianteModel
from app.infrastructure.persistence.models.ficha_model import FichaModel
from app.infrastructure.persistence.models.horario_ficha_model import HorarioFichaModel
from app.infrastructure.persistence.models.instructor_model import InstructorModel

__all__ = [
    "InstructorModel",
    "FichaModel",
    "HorarioFichaModel",
    "ClaseModel",
    "EstudianteModel",
    "AsistenciaModel",
    "ActividadModel",
    "CalificacionModel",
]
