"""Biblioteca de partidas."""
from bap_apu.contexto import Contexto
from bap_apu.data.db import Database
from bap_apu.data.repos import apu, partidas
from bap_apu.errores import ErrorValidacion
from bap_apu.services.proyectos import exigir_proyecto_propio


class PartidasService:
    def __init__(self, db: Database):
        self._db = db

    def listar(self, ctx: Contexto):
        ctx.exigir("partidas.ver")
        with self._db.lectura() as conn:
            return partidas.listar(conn)

    def detalle(self, ctx: Contexto, partida_id):
        ctx.exigir("partidas.ver")
        with self._db.lectura() as conn:
            return partidas.detalle(conn, partida_id)

    def cargar_en_proyecto(self, ctx: Contexto, partida_id, proyecto_id) -> int:
        """Copia una partida al proyecto conservando precios y cantidades del PDF."""
        ctx.exigir("partidas.usar")
        with self._db.transaccion() as conn:
            exigir_proyecto_propio(conn, proyecto_id, ctx.empresa_id)
            detalle = partidas.detalle(conn, partida_id)
            if not detalle:
                raise ErrorValidacion("La partida seleccionada no contiene recursos")
            apu.insertar_varios(conn, proyecto_id, [
                (item[1], item[2], item[5], item[4], item[6], item[7]) for item in detalle
            ])
        return len(detalle)
