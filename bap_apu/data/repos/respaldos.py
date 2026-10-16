"""Registro de los respaldos creados."""


def registrar(conn, usuario_id, ruta, hash_sha256, tamano) -> None:
    conn.execute(
        "INSERT INTO respaldos(usuario_id,ruta,hash_sha256,tamano) VALUES (?,?,?,?)",
        (usuario_id, str(ruta), hash_sha256, tamano),
    )
