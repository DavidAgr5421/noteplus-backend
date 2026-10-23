"""RN-03"""

from datetime import date

from app.domain.services.class_schedule_generator import ClassScheduleGenerator, HorarioInput


def test_genera_n_clases_martes_18():
    start = date(2026, 1, 6)  # martes
    result = ClassScheduleGenerator.generate(start, [HorarioInput(2, "18:00", 60)], 3)
    assert len(result) == 3
    assert result[0].fecha.isoformat() == "2026-01-06"
    assert result[1].fecha.isoformat() == "2026-01-13"
    assert result[2].fecha.isoformat() == "2026-01-20"
    assert all(c.hora == "18:00" for c in result)


def test_ordena_por_fecha_y_hora():
    start = date(2026, 1, 5)  # lunes
    result = ClassScheduleGenerator.generate(
        start,
        [HorarioInput(1, "08:00", 60), HorarioInput(1, "18:00", 60)],
        4,
    )
    assert len(result) == 4
    assert result[0].hora == "08:00"
    assert result[1].hora == "18:00"
