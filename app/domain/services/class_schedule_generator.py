"""RN-03: genera clases a partir de fechaInicio, horarios y totalClases."""

from dataclasses import dataclass
from datetime import date, timedelta


@dataclass(frozen=True, slots=True)
class HorarioInput:
    dia_semana: int  # 0-6
    hora: str  # HH:mm
    duracion_minutos: int = 60


@dataclass(frozen=True, slots=True)
class ClaseGenerada:
    fecha: date
    hora: str
    duracion_minutos: int


class ClassScheduleGenerator:
    @staticmethod
    def generate(
        fecha_inicio: date,
        horarios: list[HorarioInput],
        total_clases: int,
    ) -> list[ClaseGenerada]:
        if not horarios:
            raise ValueError("Debe haber al menos un horario")
        if total_clases <= 0:
            raise ValueError("totalClases debe ser > 0")

        sorted_horarios = sorted(horarios, key=lambda h: (h.dia_semana, h.hora))

        result: list[ClaseGenerada] = []
        cursor = fecha_inicio
        # 0=Monday in Python, 0=Sunday in domain → convert: (py_weekday+1)%7
        max_iter = total_clases * 14  # safety 2 weeks per class
        it = 0

        while len(result) < total_clases and it < max_iter:
            it += 1
            # Python weekday Monday=0 -> domain Sunday=0
            # domain_dia = (cursor.weekday() + 1) % 7
            domain_dia = (cursor.weekday() + 1) % 7
            for h in sorted_horarios:
                if h.dia_semana == domain_dia and cursor >= fecha_inicio:
                    result.append(
                        ClaseGenerada(fecha=cursor, hora=h.hora, duracion_minutos=h.duracion_minutos)
                    )
                    if len(result) >= total_clases:
                        break
            cursor += timedelta(days=1)

        if len(result) < total_clases:
            raise ValueError("No se pudieron generar todas las clases con los horarios dados")

        result.sort(key=lambda c: (c.fecha, c.hora))
        return result[:total_clases]
