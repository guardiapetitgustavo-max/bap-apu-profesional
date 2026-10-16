import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta

from database import conexion, conectar
from security.passwords import hash_password, validar_fortaleza, verify_password


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


def autenticar(usuario, password):
    usuario = usuario.strip()
    with conexion() as conn:
        fila = conn.execute(
            """SELECT u.id, u.usuario, u.nombre_completo, u.password_hash,
                      u.activo, u.debe_cambiar_password, u.intentos_fallidos,
                      u.bloqueado_hasta, r.nombre
               FROM usuarios u JOIN roles r ON r.id = u.rol_id
               WHERE u.usuario = ? COLLATE NOCASE""",
            (usuario,),
        ).fetchone()
        if not fila or not fila[4]:
            return None, "Usuario o contraseña incorrectos."
        ahora = datetime.now()
        if fila[7] and datetime.fromisoformat(fila[7]) > ahora:
            return None, "Cuenta bloqueada temporalmente. Intente nuevamente más tarde."
        if not verify_password(password, fila[3]):
            intentos = fila[6] + 1
            bloqueo = (ahora + timedelta(minutes=15)).isoformat(timespec="seconds") if intentos >= 5 else None
            conn.execute(
                "UPDATE usuarios SET intentos_fallidos = ?, bloqueado_hasta = ? WHERE id = ?",
                (0 if bloqueo else intentos, bloqueo, fila[0]),
            )
            conn.execute(
                "INSERT INTO auditoria(usuario_id, accion, entidad, detalle) VALUES (?, ?, ?, ?)",
                (fila[0], "LOGIN_FALLIDO", "usuarios", "Credenciales incorrectas"),
            )
            return None, "Usuario o contraseña incorrectos."

        token = secrets.token_urlsafe(32)
        conn.execute(
            "UPDATE usuarios SET intentos_fallidos=0, bloqueado_hasta=NULL, ultimo_acceso=CURRENT_TIMESTAMP WHERE id=?",
            (fila[0],),
        )
        conn.execute("INSERT INTO sesiones(usuario_id, token) VALUES (?, ?)", (fila[0], token))
        conn.execute(
            "INSERT INTO auditoria(usuario_id, accion, entidad, detalle) VALUES (?, ?, ?, ?)",
            (fila[0], "LOGIN_OK", "sesiones", "Inicio de sesión"),
        )
        permisos = frozenset(
            p[0] for p in conn.execute(
                """SELECT pe.codigo FROM permisos pe
                   JOIN rol_permisos rp ON rp.permiso_id=pe.id
                   JOIN usuarios u ON u.rol_id=rp.rol_id WHERE u.id=?""", (fila[0],)
            ).fetchall()
        )
        return UsuarioSesion(fila[0], fila[1], fila[2], fila[8], permisos, bool(fila[5]), token), None


def cambiar_password(usuario_id, password_actual, nueva_password):
    errores = validar_fortaleza(nueva_password)
    if errores:
        raise ValueError("La nueva contraseña requiere: " + ", ".join(errores) + ".")
    with conexion() as conn:
        fila = conn.execute("SELECT password_hash FROM usuarios WHERE id=?", (usuario_id,)).fetchone()
        if not fila or not verify_password(password_actual, fila[0]):
            raise ValueError("La contraseña actual no es correcta.")
        if verify_password(nueva_password, fila[0]):
            raise ValueError("La nueva contraseña debe ser diferente.")
        conn.execute(
            "UPDATE usuarios SET password_hash=?, debe_cambiar_password=0 WHERE id=?",
            (hash_password(nueva_password), usuario_id),
        )
        conn.execute(
            "INSERT INTO auditoria(usuario_id, accion, entidad, detalle) VALUES (?, ?, ?, ?)",
            (usuario_id, "PASSWORD_CAMBIADO", "usuarios", "Contraseña actualizada"),
        )


def cerrar_sesion(sesion):
    if not sesion: return
    with conexion() as conn:
        conn.execute("UPDATE sesiones SET activa=0, fin=CURRENT_TIMESTAMP WHERE token=?", (sesion.token,))
        conn.execute(
            "INSERT INTO auditoria(usuario_id, accion, entidad, detalle) VALUES (?, ?, ?, ?)",
            (sesion.id, "LOGOUT", "sesiones", "Cierre de sesión"),
        )


def listar_roles():
    with conectar() as conn:
        return conn.execute("SELECT id, nombre FROM roles ORDER BY nombre").fetchall()


def listar_usuarios():
    with conectar() as conn:
        return conn.execute(
            """SELECT u.id, u.usuario, u.nombre_completo, r.nombre, u.activo, u.ultimo_acceso
               FROM usuarios u JOIN roles r ON r.id=u.rol_id ORDER BY u.usuario"""
        ).fetchall()


def crear_usuario(actor_id, usuario, nombre, password, rol_id):
    usuario, nombre = usuario.strip(), nombre.strip()
    if not usuario or not nombre: raise ValueError("Usuario y nombre completo son obligatorios.")
    errores = validar_fortaleza(password)
    if errores: raise ValueError("La contraseña requiere: " + ", ".join(errores) + ".")
    from services.offline_license import verificar_acceso
    estado = verificar_acceso()
    with conectar() as consulta:
        activos = consulta.execute("SELECT COUNT(*) FROM usuarios WHERE activo=1").fetchone()[0]
    if activos >= estado.max_usuarios:
        raise ValueError(f"La licencia permite como máximo {estado.max_usuarios} usuarios activos.")
    with conexion() as conn:
        try:
            conn.execute(
                """INSERT INTO usuarios(usuario,nombre_completo,password_hash,rol_id,debe_cambiar_password)
                   VALUES (?,?,?,?,1)""", (usuario, nombre, hash_password(password), rol_id)
            )
        except Exception as exc:
            if "UNIQUE" in str(exc): raise ValueError("Ese nombre de usuario ya existe.") from exc
            raise
        conn.execute(
            "INSERT INTO auditoria(usuario_id,accion,entidad,detalle) VALUES (?,?,?,?)",
            (actor_id, "USUARIO_CREADO", "usuarios", usuario),
        )


def cambiar_estado_usuario(actor_id, usuario_id, activo):
    if actor_id == usuario_id and not activo:
        raise ValueError("No puede desactivar su propia cuenta.")
    with conexion() as conn:
        conn.execute("UPDATE usuarios SET activo=? WHERE id=?", (1 if activo else 0, usuario_id))
        conn.execute(
            "INSERT INTO auditoria(usuario_id,accion,entidad,detalle) VALUES (?,?,?,?)",
            (actor_id, "USUARIO_ACTIVADO" if activo else "USUARIO_DESACTIVADO", "usuarios", str(usuario_id)),
        )
