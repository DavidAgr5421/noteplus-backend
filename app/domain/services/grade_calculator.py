"""RN-14 a RN-18: cálculo de notas puro sin I/O."""

import math
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ActividadNode:
    id: str
    porcentaje: float
    parent_id: str | None


@dataclass(frozen=True, slots=True)
class CalificacionInput:
    actividad_id: str
    nota: float


@dataclass(frozen=True, slots=True)
class DetalleItem:
    actividad_id: str
    nota_efectiva: float
    porcentaje: float


@dataclass(frozen=True, slots=True)
class GradeResult:
    nota_final: float  # rounded 1 decimal
    nota_final_raw: float
    nota_acumulada: float | None
    nota_acumulada_raw: float | None
    estado: str  # APROBADO | NO_APROBADO
    detalle: list[DetalleItem]


def round_half_up(value: float, decimals: int = 1) -> float:
    """RN-18: half-up a `decimals` decimales."""
    factor = 10**decimals
    return math.floor(value * factor + 0.5 + 1e-9) / factor


class GradeCalculator:
    @staticmethod
    def calculate(
        actividades: list[ActividadNode],
        calificaciones: list[CalificacionInput],
        nota_minima_aprobacion: float,
    ) -> GradeResult:
        calif_map = {c.actividad_id: c.nota for c in calificaciones}

        children_by_parent: dict[str, list[ActividadNode]] = {}
        roots: list[ActividadNode] = []
        for act in actividades:
            if act.parent_id is None:
                roots.append(act)
            else:
                children_by_parent.setdefault(act.parent_id, []).append(act)

        def effective_nota(actividad_id: str) -> float:
            children = children_by_parent.get(actividad_id)
            if children:
                s = 0.0
                for child in children:
                    s += effective_nota(child.id) * (child.porcentaje / 100)
                return s
            return calif_map.get(actividad_id, 0.0)  # RN-17 faltantes = 0

        def is_leaf_calified(aid: str) -> bool:
            children = children_by_parent.get(aid)
            if children:
                return any(is_leaf_calified(c.id) for c in children)
            return aid in calif_map

        nota_final_raw = 0.0
        peso_calificado = 0.0
        suma_calificada = 0.0
        detalle: list[DetalleItem] = []

        for root in roots:
            ne = effective_nota(root.id)
            nota_final_raw += ne * (root.porcentaje / 100)
            detalle.append(DetalleItem(root.id, ne, root.porcentaje))
            if is_leaf_calified(root.id):
                peso_calificado += root.porcentaje
                suma_calificada += ne * (root.porcentaje / 100)

        nota_acumulada_raw: float | None = None
        nota_acumulada: float | None = None
        if peso_calificado > 0:
            nota_acumulada_raw = suma_calificada * (100 / peso_calificado)
            nota_acumulada = round_half_up(nota_acumulada_raw, 1)

        nota_final = round_half_up(nota_final_raw, 1)
        estado = "APROBADO" if nota_final_raw >= nota_minima_aprobacion else "NO_APROBADO"

        return GradeResult(
            nota_final=nota_final,
            nota_final_raw=nota_final_raw,
            nota_acumulada=nota_acumulada,
            nota_acumulada_raw=nota_acumulada_raw,
            estado=estado,
            detalle=detalle,
        )

    @staticmethod
    def validate_pesos(actividades: list[ActividadNode]) -> None:
        """RN-12: hermanos deben sumar 100 (±0.01)."""
        groups: dict[str, list[ActividadNode]] = {}
        for act in actividades:
            key = act.parent_id or "__root__"
            groups.setdefault(key, []).append(act)
        for _, group in groups.items():
            s = sum(a.porcentaje for a in group)
            if abs(s - 100) > 0.01:
                raise ValueError(f"Los porcentajes hermanos deben sumar 100 (actual: {s})")

    @staticmethod
    def promedios_por_actividad(
        actividades: list[ActividadNode],
        notas_por_actividad: dict[str, list[float]],
    ) -> dict[str, float | None]:
        """Promedio de notas por actividad (crudo, sin redondear).

        Hojas: media aritmética de sus calificaciones registradas.
        Padres: media ponderada de los promedios de sus hijos con notas
        (pesos renormalizados sobre los hijos calificados).
        Devuelve None cuando la actividad (o ningún hijo) tiene notas.
        """
        children_by_parent: dict[str, list[ActividadNode]] = {}
        for act in actividades:
            if act.parent_id is not None:
                children_by_parent.setdefault(act.parent_id, []).append(act)

        def promedio(actividad_id: str) -> float | None:
            children = children_by_parent.get(actividad_id)
            if children:
                suma = 0.0
                peso_calificado = 0.0
                for child in children:
                    pc = promedio(child.id)
                    if pc is not None:
                        suma += pc * child.porcentaje
                        peso_calificado += child.porcentaje
                if peso_calificado <= 0:
                    return None
                return suma / peso_calificado
            notas = notas_por_actividad.get(actividad_id, [])
            if not notas:
                return None
            return sum(notas) / len(notas)

        return {act.id: promedio(act.id) for act in actividades}
