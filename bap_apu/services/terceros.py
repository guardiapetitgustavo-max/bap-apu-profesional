"""Clientes y proveedores."""
from bap_apu.contexto import Contexto
from bap_apu.data.db import Database
from bap_apu.data.repos import auditoria, terceros
from bap_apu.errores import ErrorValidacion


class TercerosService:
    def __init__(self, db: Database):
        self._db = db

    def listar_clientes(self, ctx: Contexto):
        ctx.exigir("clientes.ver")
        with self._db.lectura() as conn:
            return terceros.listar_clientes(conn, ctx.empresa_id)

    def crear_cliente(self, ctx: Contexto, tipo, numero, nombre, direccion, telefono, email):
        ctx.exigir("clientes.editar")
        if not nombre.strip():
            raise ErrorValidacion("El nombre del cliente es obligatorio.")
        with self._db.transaccion() as conn:
            terceros.insertar_cliente(conn, ctx.empresa_id, tipo, numero.strip() or None, nombre.strip(),
                                      direccion.strip(), telefono.strip(), email.strip())
            auditoria.registrar(conn, ctx.usuario_id, "CLIENTE_CREADO", "clientes", nombre.strip())

    def listar_proveedores(self, ctx: Contexto):
        ctx.exigir("proveedores.ver")
        with self._db.lectura() as conn:
            return terceros.listar_proveedores(conn, ctx.empresa_id)

    def crear_proveedor(self, ctx: Contexto, ruc, nombre, contacto, telefono, email):
        ctx.exigir("proveedores.editar")
        if not nombre.strip():
            raise ErrorValidacion("El nombre del proveedor es obligatorio.")
        with self._db.transaccion() as conn:
            terceros.insertar_proveedor(conn, ctx.empresa_id, ruc.strip() or None, nombre.strip(),
                                        contacto.strip(), telefono.strip(), email.strip())
            auditoria.registrar(conn, ctx.usuario_id, "PROVEEDOR_CREADO", "proveedores", nombre.strip())
