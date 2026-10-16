"""Detalle APU de los proyectos de la empresa activa."""
from bap_apu.contexto import Contexto
from bap_apu.core.calculo import agrupar_subtotales
from bap_apu.data.db import Database
from bap_apu.data.repos import apu
from bap_apu.services.proyectos import exigir_proyecto_propio


class ApuService:
    def __init__(self, db: Database):
        self._db = db

    def detalle(self, ctx: Contexto, proyecto_id):
        ctx.exigir("apu.ver")
        with self._db.lectura() as conn:
            exigir_proyecto_propio(conn, proyecto_id, ctx.empresa_id)
            return apu.detalle(conn, proyecto_id)

    def subtotales(self, ctx: Contexto, proyecto_id) -> dict[str, float]:
        ctx.exigir("apu.ver")
        with self._db.lectura() as conn:
            exigir_proyecto_propio(conn, proyecto_id, ctx.empresa_id)
            return agrupar_subtotales(apu.tipos_y_parciales(conn, proyecto_id))

    def total(self, ctx: Contexto, proyecto_id) -> float:
        ctx.exigir("apu.ver")
        with self._db.lectura() as conn:
            exigir_proyecto_propio(conn, proyecto_id, ctx.empresa_id)
            return apu.total(conn, proyecto_id)

    def agregar_item(self, ctx: Contexto, proyecto_id, nombre, unidad, precio, cantidad, tipo) -> None:
        ctx.exigir("apu.editar")
        with self._db.transaccion() as conn:
            exigir_proyecto_propio(conn, proyecto_id, ctx.empresa_id)
            apu.insertar(conn, proyecto_id, nombre, unidad, precio, cantidad, tipo)

    def eliminar_item(self, ctx: Contexto, detalle_id) -> None:
        ctx.exigir("apu.editar")
        with self._db.transaccion() as conn:
            exigir_proyecto_propio(conn, apu.proyecto_de_item(conn, detalle_id), ctx.empresa_id)
            apu.eliminar_item(conn, detalle_id)

    def limpiar(self, ctx: Contexto, proyecto_id) -> None:
        ctx.exigir("apu.editar")
        with self._db.transaccion() as conn:
            exigir_proyecto_propio(conn, proyecto_id, ctx.empresa_id)
            apu.limpiar(conn, proyecto_id)
