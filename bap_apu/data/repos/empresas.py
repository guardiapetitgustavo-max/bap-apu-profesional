"""Acceso a la tabla de empresas."""


def actualizar_por_licencia(conn, ruc, empresa) -> None:
    """Actualiza la primera empresa con el RUC y el nombre de la licencia."""
    fila = conn.execute("SELECT id FROM empresas ORDER BY id LIMIT 1").fetchone()
    if fila:
        conn.execute(
            "UPDATE empresas SET ruc=?,razon_social=?,nombre_comercial=? WHERE id=?",
            (ruc, empresa, empresa, fila[0]),
        )


def principal_de_usuario(conn, usuario_id):
    return conn.execute(
        """SELECT e.id,e.ruc,e.razon_social,e.nombre_comercial,e.direccion,e.telefono,e.email,e.moneda
           FROM empresas e JOIN usuario_empresa ue ON ue.empresa_id=e.id
           WHERE ue.usuario_id=? AND e.activo=1
           ORDER BY ue.es_principal DESC,e.id LIMIT 1""", (usuario_id,)
    ).fetchone()


def actualizar(conn, empresa_id, ruc, razon_social, nombre_comercial, direccion, telefono, email) -> None:
    conn.execute(
        """UPDATE empresas SET ruc=?,razon_social=?,nombre_comercial=?,direccion=?,telefono=?,email=?
           WHERE id=?""",
        (ruc, razon_social, nombre_comercial, direccion, telefono, email, empresa_id),
    )


def configuracion(conn, empresa_id) -> dict:
    return dict(conn.execute("SELECT clave,valor FROM configuracion WHERE empresa_id=?", (empresa_id,)).fetchall())


def guardar_configuracion(conn, empresa_id, valores) -> None:
    for clave, valor in valores.items():
        conn.execute(
            """INSERT INTO configuracion(empresa_id,clave,valor) VALUES (?,?,?)
               ON CONFLICT(empresa_id,clave) DO UPDATE SET valor=excluded.valor""",
            (empresa_id, clave, str(valor)),
        )


def dashboard(conn, empresa_id) -> dict:
    proyectos = conn.execute("SELECT COUNT(*) FROM proyectos WHERE empresa_id=?", (empresa_id,)).fetchone()[0]
    clientes = conn.execute("SELECT COUNT(*) FROM clientes WHERE empresa_id=? AND activo=1", (empresa_id,)).fetchone()[0]
    recursos = conn.execute("SELECT COUNT(*) FROM recursos WHERE empresa_id=?", (empresa_id,)).fetchone()[0]
    partidas = conn.execute("SELECT COUNT(*) FROM partidas").fetchone()[0]
    total = conn.execute(
        """SELECT COALESCE(SUM(d.parcial),0) FROM detalle_apu d
           JOIN proyectos p ON p.id=d.proyecto_id WHERE p.empresa_id=?""", (empresa_id,)
    ).fetchone()[0]
    ultimos = conn.execute(
        """SELECT p.nombre,COALESCE(SUM(d.parcial),0) total FROM proyectos p
           LEFT JOIN detalle_apu d ON d.proyecto_id=p.id WHERE p.empresa_id=?
           GROUP BY p.id,p.nombre ORDER BY p.id DESC LIMIT 6""", (empresa_id,)
    ).fetchall()
    return {"proyectos": proyectos, "clientes": clientes, "recursos": recursos,
            "partidas": partidas, "total": total, "ultimos": ultimos}
