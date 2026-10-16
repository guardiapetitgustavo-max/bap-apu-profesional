"""Empresa, configuración, dashboard, auditoría y estado de licencia."""
from datetime import date

from bap_apu.contexto import Contexto
from bap_apu.data.db import Database
from bap_apu.data.repos import auditoria, empresas
from bap_apu.errores import ErrorValidacion
from bap_apu.services.licencias import LicenciaService


class EmpresaService:
    def __init__(self, db: Database, licencias: LicenciaService):
        self._db = db
        self._licencias = licencias

    def empresa_principal(self, usuario_id):
        with self._db.lectura() as conn:
            return empresas.principal_de_usuario(conn, usuario_id)

    def guardar_empresa(self, ctx: Contexto, ruc, razon_social, nombre_comercial, direccion, telefono, email):
        ctx.exigir("configuracion.gestionar")
        if not razon_social.strip():
            raise ErrorValidacion("La razón social es obligatoria.")
        with self._db.transaccion() as conn:
            empresas.actualizar(conn, ctx.empresa_id, ruc.strip(), razon_social.strip(),
                                nombre_comercial.strip(), direccion.strip(), telefono.strip(), email.strip())
            auditoria.registrar(conn, ctx.usuario_id, "EMPRESA_ACTUALIZADA", "empresas", str(ctx.empresa_id))

    def obtener_configuracion(self, ctx: Contexto) -> dict:
        ctx.exigir("licencias.ver")
        with self._db.lectura() as conn:
            return empresas.configuracion(conn, ctx.empresa_id)

    def guardar_configuracion(self, ctx: Contexto, valores):
        ctx.exigir("configuracion.gestionar")
        with self._db.transaccion() as conn:
            empresas.guardar_configuracion(conn, ctx.empresa_id, valores)
            auditoria.registrar(conn, ctx.usuario_id, "CONFIGURACION_ACTUALIZADA", "configuracion",
                                str(ctx.empresa_id))

    def obtener_dashboard(self, ctx: Contexto) -> dict:
        ctx.exigir("dashboard.ver")
        with self._db.lectura() as conn:
            return empresas.dashboard(conn, ctx.empresa_id)

    def listar_auditoria(self, ctx: Contexto, limite=300):
        ctx.exigir("auditoria.ver")
        with self._db.lectura() as conn:
            return auditoria.listar(conn, limite)

    def estado_licencia(self, ctx: Contexto):
        ctx.exigir("licencias.ver")
        estado = self._licencias.verificar_acceso()
        hoy = date.today().isoformat()
        vence = estado.vencimiento or "Fin de prueba en 15 días"
        plan = ("BAP APU Profesional - hasta 5 equipos / 5 usuarios"
                if estado.modo == "LICENCIA" else "Prueba gratuita BAP")
        return (estado.modo, hoy, vence, plan, estado.max_usuarios, None, 0.0)
