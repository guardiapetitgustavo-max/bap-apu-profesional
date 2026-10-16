"""Ofertas de proveedores e historial de precios."""


def ofertas(conn, empresa_id, recurso_id) -> list[tuple]:
    """Devuelve la última oferta registrada por proveedor para un recurso."""
    return conn.execute(
        """SELECT pp.id,COALESCE(p.nombre,'Proveedor sin registrar'),pp.marca,pp.precio,
                  pp.calidad,pp.stock,pp.plazo_entrega_dias,pp.fecha_precio,pp.fuente,
                  pp.proveedor_id
           FROM proveedor_precios pp
           LEFT JOIN proveedores p ON p.id=pp.proveedor_id
           WHERE pp.empresa_id=? AND pp.recurso_id=? AND pp.activo=1
             AND pp.id=(SELECT MAX(x.id) FROM proveedor_precios x
                        WHERE x.empresa_id=pp.empresa_id AND x.recurso_id=pp.recurso_id
                          AND COALESCE(x.proveedor_id,0)=COALESCE(pp.proveedor_id,0) AND x.activo=1)
           ORDER BY pp.precio ASC,pp.fecha_precio DESC""",
        (empresa_id, recurso_id),
    ).fetchall()


def oferta(conn, empresa_id, recurso_id, oferta_id):
    """(precio, proveedor_id) de una oferta activa, o None."""
    return conn.execute(
        """SELECT precio,proveedor_id FROM proveedor_precios
           WHERE id=? AND empresa_id=? AND recurso_id=? AND activo=1""",
        (oferta_id, empresa_id, recurso_id),
    ).fetchone()


def insertar_oferta(conn, empresa_id, proveedor_id, recurso_id, codigo_proveedor, descripcion, unidad,
                    marca, precio, calidad, stock, plazo_entrega_dias, fuente, fecha_precio) -> int:
    return conn.execute(
        """INSERT INTO proveedor_precios
           (empresa_id,proveedor_id,recurso_id,codigo_proveedor,descripcion,unidad,marca,
            precio,calidad,stock,plazo_entrega_dias,fuente,fecha_precio)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (empresa_id, proveedor_id, recurso_id, codigo_proveedor, descripcion, unidad, marca,
         precio, calidad, stock, plazo_entrega_dias, fuente, fecha_precio),
    ).lastrowid


def registrar_historial(conn, empresa_id, recurso_id, proveedor_id, anterior, nuevo, origen) -> None:
    conn.execute(
        """INSERT INTO historial_precios
           (empresa_id,recurso_id,proveedor_id,precio_anterior,precio_nuevo,origen)
           VALUES (?,?,?,?,?,?)""",
        (empresa_id, recurso_id, proveedor_id, anterior, nuevo, origen),
    )
