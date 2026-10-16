"""Recursos de la empresa activa y ofertas de proveedores."""
from bap_apu.contexto import Contexto
from bap_apu.data.db import Database
from bap_apu.data.repos import precios, recursos
from bap_apu.errores import ErrorValidacion


class RecursosService:
    def __init__(self, db: Database):
        self._db = db

    def listar(self, ctx: Contexto):
        ctx.exigir("recursos.ver")
        with self._db.lectura() as conn:
            return recursos.listar(conn, ctx.empresa_id)

    def crear(self, ctx: Contexto, nombre, unidad, precio, tipo) -> int:
        ctx.exigir("recursos.editar")
        with self._db.transaccion() as conn:
            return recursos.insertar(conn, nombre, unidad, precio, tipo, ctx.empresa_id)

    def ofertas(self, ctx: Contexto, recurso_id):
        ctx.exigir("recursos.ver")
        with self._db.lectura() as conn:
            return precios.ofertas(conn, ctx.empresa_id, recurso_id)

    def aplicar_oferta(self, ctx: Contexto, recurso_id, oferta_id) -> float:
        ctx.exigir("recursos.editar")
        with self._db.transaccion() as conn:
            oferta = precios.oferta(conn, ctx.empresa_id, recurso_id, oferta_id)
            if not oferta:
                raise ErrorValidacion("La oferta seleccionada no existe o ya no está activa.")
            nuevo, proveedor_id = oferta
            anterior = recursos.precio(conn, recurso_id)
            recursos.actualizar_precio(conn, recurso_id, nuevo)
            precios.registrar_historial(conn, ctx.empresa_id, recurso_id, proveedor_id,
                                        anterior, nuevo, "SELECCION_PROVEEDOR")
        return float(nuevo)
