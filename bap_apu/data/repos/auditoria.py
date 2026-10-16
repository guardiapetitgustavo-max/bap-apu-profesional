"""Registro y consulta de la bitácora de auditoría."""


def registrar(conn, usuario_id, accion, entidad, detalle) -> None:
    conn.execute(
        "INSERT INTO auditoria(usuario_id, accion, entidad, detalle) VALUES (?, ?, ?, ?)",
        (usuario_id, accion, entidad, detalle),
    )


def listar(conn, limite) -> list[tuple]:
    return conn.execute(
        """SELECT a.fecha,COALESCE(u.usuario,'SISTEMA'),a.accion,COALESCE(a.entidad,''),COALESCE(a.detalle,'')
           FROM auditoria a LEFT JOIN usuarios u ON u.id=a.usuario_id
           ORDER BY a.id DESC LIMIT ?""",
        (limite,),
    ).fetchall()
