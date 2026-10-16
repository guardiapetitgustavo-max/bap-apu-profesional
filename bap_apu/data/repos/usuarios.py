"""Consultas y escrituras de usuarios, roles, permisos y sesiones."""


def buscar_para_login(conn, usuario):
    return conn.execute(
        """SELECT u.id, u.usuario, u.nombre_completo, u.password_hash,
                  u.activo, u.debe_cambiar_password, u.intentos_fallidos,
                  u.bloqueado_hasta, r.nombre
           FROM usuarios u JOIN roles r ON r.id = u.rol_id
           WHERE u.usuario = ? COLLATE NOCASE""",
        (usuario,),
    ).fetchone()


def registrar_fallo(conn, usuario_id, intentos, bloqueo) -> None:
    conn.execute(
        "UPDATE usuarios SET intentos_fallidos = ?, bloqueado_hasta = ? WHERE id = ?",
        (intentos, bloqueo, usuario_id),
    )


def registrar_acceso(conn, usuario_id, token) -> None:
    conn.execute(
        "UPDATE usuarios SET intentos_fallidos=0, bloqueado_hasta=NULL, ultimo_acceso=CURRENT_TIMESTAMP WHERE id=?",
        (usuario_id,),
    )
    conn.execute("INSERT INTO sesiones(usuario_id, token) VALUES (?, ?)", (usuario_id, token))


def permisos_de(conn, usuario_id) -> frozenset[str]:
    return frozenset(
        p[0] for p in conn.execute(
            """SELECT pe.codigo FROM permisos pe
               JOIN rol_permisos rp ON rp.permiso_id=pe.id
               JOIN usuarios u ON u.rol_id=rp.rol_id WHERE u.id=?""",
            (usuario_id,),
        ).fetchall()
    )


def hash_de(conn, usuario_id) -> str | None:
    fila = conn.execute("SELECT password_hash FROM usuarios WHERE id=?", (usuario_id,)).fetchone()
    return fila[0] if fila else None


def actualizar_password(conn, usuario_id, hash_nuevo) -> None:
    conn.execute(
        "UPDATE usuarios SET password_hash=?, debe_cambiar_password=0 WHERE id=?",
        (hash_nuevo, usuario_id),
    )


def cerrar_sesion(conn, token) -> None:
    conn.execute("UPDATE sesiones SET activa=0, fin=CURRENT_TIMESTAMP WHERE token=?", (token,))


def listar_roles(conn):
    return conn.execute("SELECT id, nombre FROM roles ORDER BY nombre").fetchall()


def listar(conn):
    return conn.execute(
        """SELECT u.id, u.usuario, u.nombre_completo, r.nombre, u.activo, u.ultimo_acceso
           FROM usuarios u JOIN roles r ON r.id=u.rol_id ORDER BY u.usuario"""
    ).fetchall()


def contar_activos(conn) -> int:
    return conn.execute("SELECT COUNT(*) FROM usuarios WHERE activo=1").fetchone()[0]


def insertar(conn, usuario, nombre, hash_password_, rol_id) -> int:
    cur = conn.execute(
        """INSERT INTO usuarios(usuario,nombre_completo,password_hash,rol_id,debe_cambiar_password)
           VALUES (?,?,?,?,1)""",
        (usuario, nombre, hash_password_, rol_id),
    )
    return cur.lastrowid


def cambiar_estado(conn, usuario_id, activo) -> None:
    conn.execute("UPDATE usuarios SET activo=? WHERE id=?", (1 if activo else 0, usuario_id))
