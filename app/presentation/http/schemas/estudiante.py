from typing import Any

from pydantic import field_validator

from app.presentation.http.schemas.base import CamelModel

# Tipos de documento de identidad colombianos (Registraduría / Migración Colombia).
TIPOS_IDENTIFICACION = ("CC", "TI", "CE", "PA", "PEP", "PPT", "RC")

TIPO_IDENTIFICACION_LABELS = {
    "CC": "Cédula de Ciudadanía",
    "TI": "Tarjeta de Identidad",
    "CE": "Cédula de Extranjería",
    "PA": "Pasaporte",
    "PEP": "Permiso Especial de Permanencia",
    "PPT": "Permiso por Protección Temporal",
    "RC": "Registro Civil de Nacimiento",
}


def validar_tipo_identificacion(v: str | None) -> str:
    tipo = (v or "CC").strip().upper()
    if tipo not in TIPOS_IDENTIFICACION:
        raise ValueError(f"tipo_identificacion inválido, use uno de: {', '.join(TIPOS_IDENTIFICACION)}")
    return tipo


class CreateEstudianteRequest(CamelModel):
    nombre: str
    identificacion: str
    tipo_identificacion: str = "CC"
    email: str | None = None
    contacto: str | None = None

    @field_validator("nombre", "identificacion")
    @classmethod
    def not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("campo requerido")
        return v.strip()

    @field_validator("tipo_identificacion")
    @classmethod
    def valid_tipo(cls, v: str) -> str:
        return validar_tipo_identificacion(v)

    @field_validator("contacto")
    @classmethod
    def clean_contacto(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = v.strip()
        return v or None


class UpdateEstudianteRequest(CamelModel):
    nombre: str | None = None
    identificacion: str | None = None
    tipo_identificacion: str | None = None
    email: str | None = None
    contacto: str | None = None

    @field_validator("tipo_identificacion")
    @classmethod
    def valid_tipo(cls, v: str | None) -> str | None:
        if v is None:
            return None
        return validar_tipo_identificacion(v)


class EstudianteResponse(CamelModel):
    id: str
    ficha_id: str
    nombre: str
    identificacion: str
    tipo_identificacion: str = "CC"
    email: str | None = None
    contacto: str | None = None
    total_fallas: int = 0
    fallas_injustificadas: int = 0


class ImportEstudianteItem(CamelModel):
    """Un estudiante ya normalizado por el importador del frontend."""

    nombre: str
    identificacion: str
    tipo_identificacion: str = "CC"
    email: str | None = None
    contacto: str | None = None

    @field_validator("nombre", "identificacion")
    @classmethod
    def not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("campo requerido")
        return v.strip()

    @field_validator("tipo_identificacion")
    @classmethod
    def valid_tipo(cls, v: str) -> str:
        return validar_tipo_identificacion(v)


class ImportBatchRequest(CamelModel):
    """Lote tolerante: cada fila se valida por separado en la ruta.

    Las filas inválidas no tumban el lote; se reportan en `skipped`.
    """

    estudiantes: list[dict[str, Any]]


class ImportSkipped(CamelModel):
    index: int
    reason: str


class ImportBatchResponse(CamelModel):
    created: int
    skipped: list[ImportSkipped]
