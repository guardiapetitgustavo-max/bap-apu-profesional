"""Acceso a la tabla de recursos."""


def listar(conn, empresa_id) -> list[tuple]:
    return conn.execute(
        "SELECT id, nombre, unidad, precio, tipo FROM recursos WHERE empresa_id=? ORDER BY nombre COLLATE NOCASE",
        (empresa_id,),
    ).fetchall()


def insertar(conn, nombre, unidad, precio, tipo, empresa_id, codigo=None, marca=None) -> int:
    return conn.execute(
        """INSERT INTO recursos(nombre,unidad,precio,tipo,empresa_id,codigo,marca)
           VALUES (?,?,?,?,?,?,?)""",
        (nombre, unidad, precio, tipo, empresa_id, codigo, marca),
    ).lastrowid


def existentes_para_importar(conn, empresa_id) -> list[tuple]:
    return conn.execute(
        "SELECT id,codigo,nombre,unidad,precio FROM recursos WHERE empresa_id=?", (empresa_id,)
    ).fetchall()


def actualizar_datos(conn, recurso_id, empresa_id, codigo, marca, tipo) -> None:
    conn.execute(
        """UPDATE recursos SET codigo=COALESCE(NULLIF(?,''),codigo),
           marca=COALESCE(NULLIF(?,''),marca),tipo=? WHERE id=? AND empresa_id=?""",
        (codigo, marca, tipo, recurso_id, empresa_id),
    )


def precio(conn, recurso_id) -> float:
    return conn.execute("SELECT precio FROM recursos WHERE id=?", (recurso_id,)).fetchone()[0]


def actualizar_precio(conn, recurso_id, precio) -> None:
    conn.execute("UPDATE recursos SET precio=? WHERE id=?", (precio, recurso_id))
