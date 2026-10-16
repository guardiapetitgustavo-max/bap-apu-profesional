"""Proyectos de la empresa activa."""
from bap_apu.contexto import Contexto
from bap_apu.data.db import Database
from bap_apu.data.repos import apu, proyectos
from bap_apu.errores import ErrorValidacion

PROYECTO_AJENO = "El proyecto no existe o no pertenece a su empresa."


def exigir_proyecto_propio(conn, proyecto_id, empresa_id) -> None:
    """Lanza ErrorValidacion si el proyecto no es de la empresa (o no existe)."""
    if proyecto_id is None or not proyectos.pertenece(conn, proyecto_id, empresa_id):
        raise ErrorValidacion(PROYECTO_AJENO)


class ProyectosService:
    def __init__(self, db: Database):
        self._db = db

    def listar(self, ctx: Contexto):
        ctx.exigir("proyectos.ver")
        with self._db.lectura() as conn:
            return proyectos.listar(conn, ctx.empresa_id)

    def crear(self, ctx: Contexto, nombre) -> int:
        ctx.exigir("proyectos.editar")
        nombre = nombre.strip()
        if not nombre:
            raise ErrorValidacion("El nombre del proyecto es obligatorio")
        with self._db.transaccion() as conn:
            return proyectos.insertar(conn, nombre, ctx.empresa_id)

    def eliminar(self, ctx: Contexto, proyecto_id) -> None:
        """Elimina el proyecto y su detalle APU en una sola transacción."""
        ctx.exigir("proyectos.editar")
        with self._db.transaccion() as conn:
            exigir_proyecto_propio(conn, proyecto_id, ctx.empresa_id)
            apu.limpiar(conn, proyecto_id)
            proyectos.eliminar(conn, proyecto_id)
