"""Autenticación y administración de usuarios."""
import secrets
import sqlite3
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta

from bap_apu.contexto import Contexto
from bap_apu.data.db import Database
from bap_apu.data.repos import auditoria, usuarios
from bap_apu.errores import ErrorValidacion
from bap_apu.security.passwords import hash_password, validar_fortaleza, verify_password


@dataclass(frozen=True)
class UsuarioSesion:
    id: int
    usuario: str
    nombre_completo: str
    rol: str
    permisos: frozenset
    debe_cambiar_password: bool
    token: str

    def puede(self, permiso):
        return permiso in self.permisos


class AuthService:
    def __init__(self, db: Database, max_usuarios: Callable[[], int]):
        self._db = db
        self._max_usuarios = max_usuarios

    def autenticar(self, usuario: str, password: str) -> tuple[UsuarioSesion | None, str | None]:
        usuario = usuario.strip()
        # Devuelve (no lanza) en los fallos: la transacción confirma contador y auditoría.
        with self._db.transaccion() as conn:
            fila = usuarios.buscar_para_login(conn, usuario)
            if not fila or not fila[4]:
                return None, "Usuario o contraseña incorrectos."
            ahora = datetime.now()
            if fila[7] and datetime.fromisoformat(fila[7]) > ahora:
                return None, "Cuenta bloqueada temporalmente. Intente nuevamente más tarde."
            if not verify_password(password, fila[3]):
                intentos = fila[6] + 1
                bloqueo = (ahora + timedelta(minutes=15)).isoformat(timespec="seconds") if intentos >= 5 else None
                usuarios.registrar_fallo(conn, fila[0], 0 if bloqueo else intentos, bloqueo)
                auditoria.registrar(conn, fila[0], "LOGIN_FALLIDO", "usuarios", "Credenciales incorrectas")
                return None, "Usuario o contraseña incorrectos."

            token = secrets.token_urlsafe(32)
            usuarios.registrar_acceso(conn, fila[0], token)
            auditoria.registrar(conn, fila[0], "LOGIN_OK", "sesiones", "Inicio de sesión")
            permisos = usuarios.permisos_de(conn, fila[0])
            return UsuarioSesion(fila[0], fila[1], fila[2], fila[8], permisos, bool(fila[5]), token), None

    def cambiar_password(self, usuario_id: int, password_actual: str, nueva_password: str) -> None:
        errores = validar_fortaleza(nueva_password)
        if errores:
            raise ErrorValidacion("La nueva contraseña requiere: " + ", ".join(errores) + ".")
        with self._db.transaccion() as conn:
            actual = usuarios.hash_de(conn, usuario_id)
            if actual is None or not verify_password(password_actual, actual):
                raise ErrorValidacion("La contraseña actual no es correcta.")
            if verify_password(nueva_password, actual):
                raise ErrorValidacion("La nueva contraseña debe ser diferente.")
            usuarios.actualizar_password(conn, usuario_id, hash_password(nueva_password))
            auditoria.registrar(conn, usuario_id, "PASSWORD_CAMBIADO", "usuarios", "Contraseña actualizada")

    def cerrar_sesion(self, sesion) -> None:
        if not sesion:
            return
        with self._db.transaccion() as conn:
            usuarios.cerrar_sesion(conn, sesion.token)
            auditoria.registrar(conn, sesion.id, "LOGOUT", "sesiones", "Cierre de sesión")

    def listar_roles(self, ctx: Contexto):
        ctx.exigir("usuarios.gestionar")
        with self._db.lectura() as conn:
            return usuarios.listar_roles(conn)

    def listar_usuarios(self, ctx: Contexto):
        ctx.exigir("usuarios.gestionar")
        with self._db.lectura() as conn:
            return usuarios.listar(conn)

    def crear_usuario(self, ctx: Contexto, usuario: str, nombre: str, password: str, rol_id: int) -> None:
        ctx.exigir("usuarios.gestionar")
        usuario, nombre = usuario.strip(), nombre.strip()
        if not usuario or not nombre:
            raise ErrorValidacion("Usuario y nombre completo son obligatorios.")
        errores = validar_fortaleza(password)
        if errores:
            raise ErrorValidacion("La contraseña requiere: " + ", ".join(errores) + ".")
        limite = self._max_usuarios()
        with self._db.transaccion() as conn:
            if usuarios.contar_activos(conn) >= limite:
                raise ErrorValidacion(f"La licencia permite como máximo {limite} usuarios activos.")
            try:
                usuarios.insertar(conn, usuario, nombre, hash_password(password), rol_id)
            except sqlite3.IntegrityError as exc:
                if "UNIQUE" in str(exc):
                    raise ErrorValidacion("Ese nombre de usuario ya existe.") from exc
                raise
            auditoria.registrar(conn, ctx.usuario_id, "USUARIO_CREADO", "usuarios", usuario)

    def cambiar_estado_usuario(self, ctx: Contexto, usuario_id: int, activo: bool) -> None:
        ctx.exigir("usuarios.gestionar")
        if ctx.usuario_id == usuario_id and not activo:
            raise ErrorValidacion("No puede desactivar su propia cuenta.")
        with self._db.transaccion() as conn:
            usuarios.cambiar_estado(conn, usuario_id, activo)
            auditoria.registrar(
                conn, ctx.usuario_id,
                "USUARIO_ACTIVADO" if activo else "USUARIO_DESACTIVADO", "usuarios", str(usuario_id),
            )
