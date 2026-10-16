"""Registro de importaciones de recursos."""


def registrar(conn, empresa_id, usuario_id, archivo, formato, filas, nuevos, actualizados,
              ofertas, omitidos) -> None:
    conn.execute(
        """INSERT INTO importaciones_recursos
           (empresa_id,usuario_id,archivo,formato,filas,nuevos,actualizados,ofertas,omitidos)
           VALUES (?,?,?,?,?,?,?,?,?)""",
        (empresa_id, usuario_id, archivo, formato, filas, nuevos, actualizados, ofertas, omitidos),
    )
