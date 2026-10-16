"""Acceso a la tabla de proyectos."""


def listar(conn, empresa_id) -> list[tuple]:
    return conn.execute(
        "SELECT id, nombre FROM proyectos WHERE empresa_id=? ORDER BY nombre COLLATE NOCASE", (empresa_id,)
    ).fetchall()


def insertar(conn, nombre, empresa_id) -> int:
    return conn.execute(
        "INSERT INTO proyectos (nombre, empresa_id, creado_en) VALUES (?, ?, CURRENT_TIMESTAMP)",
        (nombre, empresa_id),
    ).lastrowid


def pertenece(conn, proyecto_id, empresa_id) -> bool:
    return conn.execute(
        "SELECT 1 FROM proyectos WHERE id=? AND empresa_id=?", (proyecto_id, empresa_id)
    ).fetchone() is not None


def eliminar(conn, proyecto_id) -> None:
    conn.execute("DELETE FROM proyectos WHERE id = ?", (proyecto_id,))
