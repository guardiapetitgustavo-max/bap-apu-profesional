"""Acceso al detalle APU de los proyectos."""


def detalle(conn, proyecto_id) -> list[tuple]:
    return conn.execute(
        """SELECT id, nombre, unidad, precio, cantidad, parcial, tipo
           FROM detalle_apu WHERE proyecto_id = ?""",
        (proyecto_id,),
    ).fetchall()


def tipos_y_parciales(conn, proyecto_id) -> list[tuple]:
    return conn.execute(
        "SELECT tipo, SUM(parcial) FROM detalle_apu WHERE proyecto_id = ? GROUP BY tipo",
        (proyecto_id,),
    ).fetchall()


def total(conn, proyecto_id) -> float:
    valor = conn.execute(
        "SELECT SUM(parcial) FROM detalle_apu WHERE proyecto_id = ?", (proyecto_id,)
    ).fetchone()[0]
    return round(valor, 2) if valor is not None else 0.0


def insertar(conn, proyecto_id, nombre, unidad, precio, cantidad, tipo) -> None:
    parcial = round(float(precio) * float(cantidad), 2)
    conn.execute(
        """INSERT INTO detalle_apu (proyecto_id, nombre, unidad, precio, cantidad, parcial, tipo)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (proyecto_id, nombre, unidad, precio, cantidad, parcial, tipo),
    )


def insertar_varios(conn, proyecto_id, filas) -> None:
    """Inserta filas (nombre, unidad, precio, cantidad, parcial, tipo) tal como vienen."""
    conn.executemany(
        """INSERT INTO detalle_apu (proyecto_id, nombre, unidad, precio, cantidad, parcial, tipo)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        [(proyecto_id, *fila) for fila in filas],
    )


def proyecto_de_item(conn, detalle_id) -> int | None:
    fila = conn.execute("SELECT proyecto_id FROM detalle_apu WHERE id = ?", (detalle_id,)).fetchone()
    return fila[0] if fila else None


def eliminar_item(conn, detalle_id) -> None:
    conn.execute("DELETE FROM detalle_apu WHERE id = ?", (detalle_id,))


def limpiar(conn, proyecto_id) -> None:
    conn.execute("DELETE FROM detalle_apu WHERE proyecto_id = ?", (proyecto_id,))
