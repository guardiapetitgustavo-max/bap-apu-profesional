"""Acceso a la tabla de empresas."""


def actualizar_por_licencia(conn, ruc, empresa) -> None:
    """Actualiza la primera empresa con el RUC y el nombre de la licencia."""
    fila = conn.execute("SELECT id FROM empresas ORDER BY id LIMIT 1").fetchone()
    if fila:
        conn.execute(
            "UPDATE empresas SET ruc=?,razon_social=?,nombre_comercial=? WHERE id=?",
            (ruc, empresa, empresa, fila[0]),
        )
