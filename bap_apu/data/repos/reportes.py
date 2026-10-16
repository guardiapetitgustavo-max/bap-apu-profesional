"""Consultas de los reportes (mismas columnas que el reporte legado)."""


def proyectos_resumen(conn, empresa_id) -> list[tuple]:
    return conn.execute(
        """SELECT p.id,p.nombre,p.estado,COALESCE(c.nombre,''),COALESCE(SUM(d.parcial),0)
           FROM proyectos p LEFT JOIN clientes c ON c.id=p.cliente_id
           LEFT JOIN detalle_apu d ON d.proyecto_id=p.id WHERE p.empresa_id=?
           GROUP BY p.id,p.nombre,p.estado,c.nombre ORDER BY p.nombre""",
        (empresa_id,),
    ).fetchall()


def recursos(conn, empresa_id) -> list[tuple]:
    return conn.execute(
        "SELECT nombre,unidad,precio,tipo FROM recursos WHERE empresa_id=? ORDER BY tipo,nombre",
        (empresa_id,),
    ).fetchall()


def partidas(conn) -> list[tuple]:
    return conn.execute("SELECT nombre,unidad,costo_referencia FROM partidas ORDER BY nombre").fetchall()


def precios_proveedores(conn, empresa_id) -> list[tuple]:
    return conn.execute(
        """SELECT r.nombre,COALESCE(p.nombre,''),pp.marca,pp.precio,pp.calidad,pp.stock,
                  pp.plazo_entrega_dias,pp.fecha_precio,COALESCE(pp.fuente,'')
           FROM proveedor_precios pp JOIN recursos r ON r.id=pp.recurso_id
           LEFT JOIN proveedores p ON p.id=pp.proveedor_id
           WHERE pp.empresa_id=? ORDER BY r.nombre,pp.fecha_precio DESC""",
        (empresa_id,),
    ).fetchall()


def historial_precios(conn, empresa_id) -> list[tuple]:
    return conn.execute(
        """SELECT h.fecha,r.nombre,h.precio_anterior,h.precio_nuevo,h.origen,COALESCE(p.nombre,'')
           FROM historial_precios h JOIN recursos r ON r.id=h.recurso_id
           LEFT JOIN proveedores p ON p.id=h.proveedor_id
           WHERE h.empresa_id=? ORDER BY h.id DESC""",
        (empresa_id,),
    ).fetchall()
