from datetime import date

from pydantic import field_validator

from app.presentation.http.schemas.base import CamelModel


class HorarioInput(CamelModel):
    dia_semana: int  # 0-6
    hora: str  # HH:mm
    duracion_minutos: int = 60

    @field_validator("dia_semana")
    @classmethod
    def check_dia(cls, v: int) -> int:
        if v < 0 or v > 6:
            raise ValueError("dia_semana debe ser 0-6")
        return v

    @field_validator("hora")
    @classmethod
    def check_hora(cls, v: str) -> str:
        import re

        if not re.match(r"^\d{2}:\d{2}$", v):
            raise ValueError("hora debe ser HH:mm")
        h, m = map(int, v.split(":"))
        if not (0 <= h <= 23 and 0 <= m <= 59):
            raise ValueError("hora inválida")
        return v


class CreateFichaRequest(CamelModel):
    codigo: str
    nombre: str
    fecha_inicio: date
    trimestre: str | None = None
    total_clases: int
    nota_minima_aprobacion: float
    horarios: list[HorarioInput]

    @field_validator("codigo")
    @classmethod
    def check_codigo(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("código requerido")
        return v.strip()

    @field_validator("trimestre")
    @classmethod
    def check_trimestre(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip()
        if not v:
            raise ValueError("trimestre requerido")
        if len(v) > 20:
            raise ValueError("trimestre máximo 20 caracteres")
        return v

    @field_validator("total_clases")
    @classmethod
    def check_total(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("total_clases > 0")
        return v

    @field_validator("nota_minima_aprobacion")
    @classmethod
    def check_nota(cls, v: float) -> float:
        if v < 0 or v > 5:
            raise ValueError("nota_minima entre 0 y 5")
        return v


class UpdateFichaRequest(CamelModel):
    codigo: str | None = None
    nombre: str | None = None
    fecha_inicio: date | None = None
    trimestre: str | None = None
    total_clases: int | None = None
    nota_minima_aprobacion: float | None = None
    horarios: list[HorarioInput] | None = None


class FichaResponse(CamelModel):
    id: str
    codigo: str
    nombre: str
    fecha_inicio: date
    trimestre: str
    total_clases: int
    nota_minima_aprobacion: float
    archivada: bool
    finalizada: bool
    instructor_id: str
    horarios: list[HorarioInput] = []
    numero_estudiantes: int = 0
    clases_restantes: int = 0
