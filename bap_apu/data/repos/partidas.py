"""Acceso a la biblioteca de partidas."""


def listar(conn) -> list[tuple]:
    return conn.execute(
        """SELECT id, nombre, unidad, costo_referencia
           FROM partidas ORDER BY nombre COLLATE NOCASE"""
    ).fetchall()


def detalle(conn, partida_id) -> list[tuple]:
    return conn.execute(
        """SELECT id, nombre, unidad, cuadrilla, cantidad, precio, parcial, tipo
           FROM partida_detalle WHERE partida_id = ?
           ORDER BY CASE tipo
               WHEN 'Mano de Obra' THEN 1
               WHEN 'Material' THEN 2
               WHEN 'Equipo' THEN 3
               ELSE 4 END, id""",
        (partida_id,),
    ).fetchall()
