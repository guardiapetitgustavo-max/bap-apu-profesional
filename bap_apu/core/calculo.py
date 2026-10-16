"""Cálculos del APU."""
from collections.abc import Iterable
from decimal import ROUND_HALF_UP, Decimal

_CLAVES = {
    "Mano de obra": "Mano de Obra",
    "Material": "Materiales", "Materiales": "Materiales",
    "Equipo": "Equipo", "Equipos": "Equipo",
}


def agrupar_subtotales(filas: Iterable[tuple[str, float | None]]) -> dict[str, float]:
    """Suma los parciales por tipo (Mano de Obra, Materiales, Equipo).

    Normaliza el tipo como la versión 1.4.0 (`strip().capitalize()`); las variantes
    del mismo tipo se suman y los tipos no reconocidos se ignoran.
    Cada subtotal se redondea a 2 decimales con medio hacia arriba.
    """
    subtotales = {"Mano de Obra": 0, "Materiales": 0, "Equipo": 0}
    for tipo, total in filas:
        if total is None:
            continue
        clave = _CLAVES.get(tipo.strip().capitalize())
        if clave:
            subtotales[clave] += total
    return {clave: redondear(valor) for clave, valor in subtotales.items()}


def redondear(valor: float) -> float:
    """Redondea a 2 decimales con medio hacia arriba, sobre el valor decimal escrito (5.555 -> 5.56)."""
    return float(Decimal(str(valor)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
