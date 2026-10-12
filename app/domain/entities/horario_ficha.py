from dataclasses import dataclass


@dataclass(slots=True)
class HorarioFicha:
    id: str
    ficha_id: str
    dia_semana: int  # 0-6
    hora: str  # HH:mm
    duracion_minutos: int = 60
