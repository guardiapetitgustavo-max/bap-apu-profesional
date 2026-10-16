"""Datos iniciales: roles, permisos, administrador, empresa, planes y licencia.

Copia literal de `_sembrar_seguridad` y `_sembrar_empresa_y_planes` de
`database.py` (commit 71fd64f). Es idempotente y se ejecuta en cada arranque.
"""


def sembrar(conn):
    cursor = conn.cursor()
    _sembrar_seguridad(cursor)
    _sembrar_empresa_y_planes(cursor)


def _sembrar_seguridad(cursor):
    roles = {
        "Administrador": "Control completo del sistema",
        "Gerente": "Consulta y gestión operativa sin administrar usuarios",
        "Ingeniero": "Gestión de proyectos, recursos y APU",
        "Presupuestador": "Creación y edición de APU",
        "Consulta": "Acceso de solo lectura",
    }
    permisos = {
        "proyectos.ver": "Ver proyectos", "proyectos.editar": "Crear y eliminar proyectos",
        "recursos.ver": "Ver recursos", "recursos.editar": "Crear recursos",
        "partidas.ver": "Ver biblioteca de partidas", "partidas.usar": "Cargar partidas a proyectos",
        "apu.ver": "Ver APU", "apu.editar": "Modificar APU", "apu.exportar": "Exportar PDF",
        "usuarios.gestionar": "Crear y administrar usuarios",
        "dashboard.ver": "Ver indicadores generales",
        "empresas.gestionar": "Administrar empresas",
        "clientes.ver": "Ver clientes", "clientes.editar": "Administrar clientes",
        "proveedores.ver": "Ver proveedores", "proveedores.editar": "Administrar proveedores",
        "reportes.ver": "Ver reportes", "reportes.exportar": "Exportar Excel",
        "auditoria.ver": "Consultar auditoría",
        "respaldos.gestionar": "Crear respaldos",
        "configuracion.gestionar": "Configurar empresa",
        "licencias.ver": "Consultar plan y licencia",
    }
    for nombre, descripcion in roles.items():
        cursor.execute("INSERT OR IGNORE INTO roles(nombre, descripcion) VALUES (?, ?)", (nombre, descripcion))
    for codigo, descripcion in permisos.items():
        cursor.execute("INSERT OR IGNORE INTO permisos(codigo, descripcion) VALUES (?, ?)", (codigo, descripcion))

    mapas = {
        "Administrador": set(permisos),
        "Gerente": set(permisos) - {"usuarios.gestionar", "empresas.gestionar"},
        "Ingeniero": {"dashboard.ver", "proyectos.ver", "proyectos.editar", "recursos.ver", "recursos.editar", "partidas.ver", "partidas.usar", "apu.ver", "apu.editar", "apu.exportar", "clientes.ver", "proveedores.ver", "reportes.ver", "reportes.exportar", "licencias.ver"},
        "Presupuestador": {"dashboard.ver", "proyectos.ver", "recursos.ver", "partidas.ver", "partidas.usar", "apu.ver", "apu.editar", "apu.exportar", "clientes.ver", "reportes.ver", "reportes.exportar", "licencias.ver"},
        "Consulta": {"dashboard.ver", "proyectos.ver", "recursos.ver", "partidas.ver", "apu.ver", "clientes.ver", "proveedores.ver", "reportes.ver", "licencias.ver"},
    }
    for rol, codigos in mapas.items():
        rol_id = cursor.execute("SELECT id FROM roles WHERE nombre = ?", (rol,)).fetchone()[0]
        for codigo in codigos:
            permiso_id = cursor.execute("SELECT id FROM permisos WHERE codigo = ?", (codigo,)).fetchone()[0]
            cursor.execute("INSERT OR IGNORE INTO rol_permisos(rol_id, permiso_id) VALUES (?, ?)", (rol_id, permiso_id))

    if cursor.execute("SELECT COUNT(*) FROM usuarios").fetchone()[0] == 0:
        from bap_apu.security.passwords import hash_password
        rol_id = cursor.execute("SELECT id FROM roles WHERE nombre = 'Administrador'").fetchone()[0]
        cursor.execute(
            """INSERT INTO usuarios
               (usuario, nombre_completo, password_hash, rol_id, debe_cambiar_password)
               VALUES (?, ?, ?, ?, 1)""",
            ("admin", "Administrador del sistema", hash_password("admin123"), rol_id),
        )



def _sembrar_empresa_y_planes(cursor):
    planes = [
        ("BASICO", "Básico", 1, 10, 59.0),
        ("PRO", "Profesional", 5, None, 129.0),
        ("EMPRESA", "Empresa", 20, None, 299.0),
        ("CORP", "Corporativo", 999, None, 0.0),
    ]
    cursor.executemany(
        "INSERT OR IGNORE INTO planes(codigo,nombre,max_usuarios,max_proyectos,precio_mensual) VALUES (?,?,?,?,?)",
        planes,
    )
    if cursor.execute("SELECT COUNT(*) FROM empresas").fetchone()[0] == 0:
        cursor.execute(
            """INSERT INTO empresas(ruc,razon_social,nombre_comercial,direccion,email)
               VALUES (?,?,?,?,?)""",
            (None, "Mi Empresa", "Mi Empresa", "", ""),
        )
    empresa_id = cursor.execute("SELECT id FROM empresas ORDER BY id LIMIT 1").fetchone()[0]
    cursor.execute("UPDATE proyectos SET empresa_id=? WHERE empresa_id IS NULL", (empresa_id,))
    cursor.execute("UPDATE recursos SET empresa_id=? WHERE empresa_id IS NULL", (empresa_id,))
    for (usuario_id,) in cursor.execute("SELECT id FROM usuarios").fetchall():
        cursor.execute(
            "INSERT OR IGNORE INTO usuario_empresa(usuario_id,empresa_id,es_principal) VALUES (?,?,1)",
            (usuario_id, empresa_id),
        )
    if cursor.execute("SELECT COUNT(*) FROM licencias").fetchone()[0] == 0:
        from datetime import date, timedelta
        plan_id = cursor.execute("SELECT id FROM planes WHERE codigo='PRO'").fetchone()[0]
        inicio = date.today()
        cursor.execute(
            """INSERT INTO licencias(empresa_id,plan_id,estado,inicio,vencimiento,ultimo_control)
               VALUES (?,?,?,?,?,CURRENT_TIMESTAMP)""",
            (empresa_id, plan_id, "PRUEBA", inicio.isoformat(), (inicio + timedelta(days=15)).isoformat()),
        )
