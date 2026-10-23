"""RN-17, RN-18"""

from app.domain.services.grade_calculator import ActividadNode, CalificacionInput, GradeCalculator


def test_nota_final_faltantes_como_cero():
    acts = [ActividadNode("a1", 50, None), ActividadNode("a2", 50, None)]
    cals = [CalificacionInput("a1", 4.0)]
    r = GradeCalculator.calculate(acts, cals, 3.0)
    assert abs(r.nota_final_raw - 2.0) < 1e-9
    assert r.nota_final == 2.0
    assert r.estado == "NO_APROBADO"


def test_nota_acumulada_normalizada():
    acts = [ActividadNode("a1", 50, None), ActividadNode("a2", 50, None)]
    cals = [CalificacionInput("a1", 4.0)]
    r = GradeCalculator.calculate(acts, cals, 3.0)
    assert r.nota_acumulada_raw == 4.0
    assert r.nota_acumulada == 4.0


def test_subactividades_ponderadas_rn14():
    acts = [
        ActividadNode("padre", 100, None),
        ActividadNode("h1", 60, "padre"),
        ActividadNode("h2", 40, "padre"),
    ]
    cals = [CalificacionInput("h1", 5.0), CalificacionInput("h2", 3.0)]
    r = GradeCalculator.calculate(acts, cals, 3.0)
    assert abs(r.nota_final_raw - 4.2) < 1e-9
    assert r.estado == "APROBADO"


def test_redondeo_half_up():
    from app.domain.services.grade_calculator import round_half_up

    assert round_half_up(3.05, 1) == 3.1
    assert round_half_up(3.04, 1) == 3.0


def test_promedios_hojas_y_sin_notas():
    acts = [ActividadNode("a1", 50, None), ActividadNode("a2", 50, None)]
    r = GradeCalculator.promedios_por_actividad(acts, {"a1": [4.0, 5.0]})
    assert abs(r["a1"] - 4.5) < 1e-9
    assert r["a2"] is None


def test_promedios_padre_ponderado_renormalizado():
    acts = [
        ActividadNode("padre", 100, None),
        ActividadNode("h1", 60, "padre"),
        ActividadNode("h2", 40, "padre"),
    ]
    # solo h1 calificada -> el promedio del padre es el de h1 (peso renormalizado)
    r = GradeCalculator.promedios_por_actividad(acts, {"h1": [5.0]})
    assert abs(r["padre"] - 5.0) < 1e-9
    # ambas calificadas -> 5*0.6 + 3*0.4 = 4.2
    r = GradeCalculator.promedios_por_actividad(acts, {"h1": [5.0], "h2": [3.0]})
    assert abs(r["padre"] - 4.2) < 1e-9
    # nadie calificado -> None en padre e hijos
    r = GradeCalculator.promedios_por_actividad(acts, {})
    assert r["padre"] is None
    assert r["h1"] is None
