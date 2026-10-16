"""Acceso a clientes y proveedores."""


def listar_clientes(conn, empresa_id) -> list[tuple]:
    return conn.execute(
        """SELECT id,tipo_documento,numero_documento,nombre,direccion,telefono,email,activo
           FROM clientes WHERE empresa_id=? ORDER BY nombre COLLATE NOCASE""", (empresa_id,)
    ).fetchall()


def insertar_cliente(conn, empresa_id, tipo, numero, nombre, direccion, telefono, email) -> None:
    conn.execute(
        """INSERT INTO clientes(empresa_id,tipo_documento,numero_documento,nombre,direccion,telefono,email)
           VALUES (?,?,?,?,?,?,?)""",
        (empresa_id, tipo, numero, nombre, direccion, telefono, email),
    )


def listar_proveedores(conn, empresa_id) -> list[tuple]:
    return conn.execute(
        """SELECT id,ruc,nombre,contacto,telefono,email,activo FROM proveedores
           WHERE empresa_id=? ORDER BY nombre COLLATE NOCASE""", (empresa_id,)
    ).fetchall()


def insertar_proveedor(conn, empresa_id, ruc, nombre, contacto, telefono, email) -> None:
    conn.execute(
        """INSERT INTO proveedores(empresa_id,ruc,nombre,contacto,telefono,email)
           VALUES (?,?,?,?,?,?)""",
        (empresa_id, ruc, nombre, contacto, telefono, email),
    )


def buscar_proveedor_por_ruc(conn, empresa_id, ruc):
    return conn.execute(
        "SELECT id FROM proveedores WHERE empresa_id=? AND ruc=?", (empresa_id, ruc)
    ).fetchone()


def buscar_proveedor_por_nombre(conn, empresa_id, nombre):
    return conn.execute(
        "SELECT id FROM proveedores WHERE empresa_id=? AND nombre=? COLLATE NOCASE", (empresa_id, nombre)
    ).fetchone()


def insertar_proveedor_minimo(conn, empresa_id, ruc, nombre) -> int:
    cursor = conn.execute(
        "INSERT INTO proveedores(empresa_id,ruc,nombre) VALUES (?,?,?)", (empresa_id, ruc, nombre)
    )
    return cursor.lastrowid
