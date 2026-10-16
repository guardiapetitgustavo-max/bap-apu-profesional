"""Migración 1: esquema de BAP APU Profesional 1.4.0.

Copia literal de las sentencias de `database.crear_tablas()` (commit 71fd64f)
más la tabla `control_prueba` de `offline_license.inicializar_control_prueba`.
Es idempotente frente a bases 1.4.0 existentes. No hace commit.
"""


def aplicar(conn):
    cursor = conn.cursor()

    # ---------------- PROYECTOS ----------------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS proyectos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL
    )
    """)

    # ---------------- RECURSOS ----------------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS recursos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL,
        unidad TEXT NOT NULL,
        precio REAL NOT NULL CHECK (precio >= 0),
        tipo TEXT NOT NULL
    )
    """)

    # ---------------- DETALLE APU ----------------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS detalle_apu (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        proyecto_id INTEGER,
        nombre TEXT,
        unidad TEXT,
        precio REAL,
        cantidad REAL,
        parcial REAL,
        tipo TEXT
    )
    """)

    # Biblioteca de partidas importadas desde documentos APU.
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS partidas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL,
        unidad TEXT NOT NULL,
        rendimiento_mo REAL DEFAULT 0,
        rendimiento_eq REAL DEFAULT 0,
        costo_referencia REAL NOT NULL DEFAULT 0,
        fuente TEXT,
        UNIQUE(nombre, unidad)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS partida_detalle (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        partida_id INTEGER NOT NULL,
        nombre TEXT NOT NULL,
        unidad TEXT NOT NULL,
        cuadrilla REAL DEFAULT 0,
        cantidad REAL NOT NULL,
        precio REAL NOT NULL,
        parcial REAL NOT NULL,
        tipo TEXT NOT NULL,
        FOREIGN KEY(partida_id) REFERENCES partidas(id) ON DELETE CASCADE
    )
    """)

    # Seguridad, roles y sesiones.
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS roles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL UNIQUE,
        descripcion TEXT
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS permisos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        codigo TEXT NOT NULL UNIQUE,
        descripcion TEXT NOT NULL
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS rol_permisos (
        rol_id INTEGER NOT NULL,
        permiso_id INTEGER NOT NULL,
        PRIMARY KEY (rol_id, permiso_id),
        FOREIGN KEY(rol_id) REFERENCES roles(id) ON DELETE CASCADE,
        FOREIGN KEY(permiso_id) REFERENCES permisos(id) ON DELETE CASCADE
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario TEXT NOT NULL UNIQUE COLLATE NOCASE,
        nombre_completo TEXT NOT NULL,
        password_hash TEXT NOT NULL,
        rol_id INTEGER NOT NULL,
        activo INTEGER NOT NULL DEFAULT 1,
        debe_cambiar_password INTEGER NOT NULL DEFAULT 1,
        intentos_fallidos INTEGER NOT NULL DEFAULT 0,
        bloqueado_hasta TEXT,
        creado_en TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        ultimo_acceso TEXT,
        FOREIGN KEY(rol_id) REFERENCES roles(id)
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sesiones (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario_id INTEGER NOT NULL,
        token TEXT NOT NULL UNIQUE,
        inicio TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        fin TEXT,
        activa INTEGER NOT NULL DEFAULT 1,
        FOREIGN KEY(usuario_id) REFERENCES usuarios(id)
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS auditoria (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario_id INTEGER,
        accion TEXT NOT NULL,
        entidad TEXT,
        detalle TEXT,
        fecha TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(usuario_id) REFERENCES usuarios(id)
    )
    """)

    # Entidades comerciales y configuración multiempresa.
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS empresas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ruc TEXT UNIQUE,
        razon_social TEXT NOT NULL,
        nombre_comercial TEXT,
        direccion TEXT,
        telefono TEXT,
        email TEXT,
        moneda TEXT NOT NULL DEFAULT 'PEN',
        activo INTEGER NOT NULL DEFAULT 1,
        creado_en TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS usuario_empresa (
        usuario_id INTEGER NOT NULL,
        empresa_id INTEGER NOT NULL,
        es_principal INTEGER NOT NULL DEFAULT 0,
        PRIMARY KEY(usuario_id, empresa_id),
        FOREIGN KEY(usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE,
        FOREIGN KEY(empresa_id) REFERENCES empresas(id) ON DELETE CASCADE
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS clientes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        empresa_id INTEGER NOT NULL,
        tipo_documento TEXT NOT NULL DEFAULT 'RUC',
        numero_documento TEXT,
        nombre TEXT NOT NULL,
        direccion TEXT,
        telefono TEXT,
        email TEXT,
        activo INTEGER NOT NULL DEFAULT 1,
        creado_en TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(empresa_id) REFERENCES empresas(id),
        UNIQUE(empresa_id, numero_documento)
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS proveedores (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        empresa_id INTEGER NOT NULL,
        ruc TEXT,
        nombre TEXT NOT NULL,
        contacto TEXT,
        telefono TEXT,
        email TEXT,
        activo INTEGER NOT NULL DEFAULT 1,
        creado_en TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(empresa_id) REFERENCES empresas(id),
        UNIQUE(empresa_id, ruc)
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS configuracion (
        empresa_id INTEGER NOT NULL,
        clave TEXT NOT NULL,
        valor TEXT,
        PRIMARY KEY(empresa_id, clave),
        FOREIGN KEY(empresa_id) REFERENCES empresas(id) ON DELETE CASCADE
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS planes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        codigo TEXT NOT NULL UNIQUE,
        nombre TEXT NOT NULL,
        max_usuarios INTEGER NOT NULL,
        max_proyectos INTEGER,
        precio_mensual REAL NOT NULL,
        activo INTEGER NOT NULL DEFAULT 1
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS licencias (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        empresa_id INTEGER NOT NULL UNIQUE,
        plan_id INTEGER NOT NULL,
        clave TEXT UNIQUE,
        estado TEXT NOT NULL DEFAULT 'PRUEBA',
        inicio TEXT NOT NULL,
        vencimiento TEXT NOT NULL,
        ultimo_control TEXT,
        FOREIGN KEY(empresa_id) REFERENCES empresas(id),
        FOREIGN KEY(plan_id) REFERENCES planes(id)
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS respaldos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario_id INTEGER,
        ruta TEXT NOT NULL,
        hash_sha256 TEXT NOT NULL,
        tamano INTEGER NOT NULL,
        creado_en TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(usuario_id) REFERENCES usuarios(id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS proveedor_precios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        empresa_id INTEGER NOT NULL,
        proveedor_id INTEGER,
        recurso_id INTEGER NOT NULL,
        codigo_proveedor TEXT,
        descripcion TEXT,
        unidad TEXT NOT NULL,
        marca TEXT,
        precio REAL NOT NULL CHECK(precio > 0),
        moneda TEXT NOT NULL DEFAULT 'PEN',
        calidad INTEGER CHECK(calidad BETWEEN 1 AND 5),
        stock REAL,
        plazo_entrega_dias INTEGER,
        fuente TEXT,
        fecha_precio TEXT NOT NULL,
        importado_en TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        activo INTEGER NOT NULL DEFAULT 1,
        FOREIGN KEY(empresa_id) REFERENCES empresas(id),
        FOREIGN KEY(proveedor_id) REFERENCES proveedores(id),
        FOREIGN KEY(recurso_id) REFERENCES recursos(id) ON DELETE CASCADE
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS historial_precios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        empresa_id INTEGER NOT NULL,
        recurso_id INTEGER NOT NULL,
        proveedor_id INTEGER,
        precio_anterior REAL,
        precio_nuevo REAL NOT NULL,
        origen TEXT NOT NULL,
        fecha TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(empresa_id) REFERENCES empresas(id),
        FOREIGN KEY(recurso_id) REFERENCES recursos(id) ON DELETE CASCADE,
        FOREIGN KEY(proveedor_id) REFERENCES proveedores(id)
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS importaciones_recursos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        empresa_id INTEGER NOT NULL,
        usuario_id INTEGER,
        archivo TEXT NOT NULL,
        formato TEXT NOT NULL,
        filas INTEGER NOT NULL,
        nuevos INTEGER NOT NULL,
        actualizados INTEGER NOT NULL,
        ofertas INTEGER NOT NULL,
        omitidos INTEGER NOT NULL,
        creado_en TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(empresa_id) REFERENCES empresas(id),
        FOREIGN KEY(usuario_id) REFERENCES usuarios(id)
    )
    """)

    _agregar_columna_si_falta(cursor, "proyectos", "empresa_id", "INTEGER")
    _agregar_columna_si_falta(cursor, "proyectos", "cliente_id", "INTEGER")
    _agregar_columna_si_falta(cursor, "proyectos", "estado", "TEXT NOT NULL DEFAULT 'ACTIVO'")
    _agregar_columna_si_falta(cursor, "proyectos", "presupuesto", "REAL NOT NULL DEFAULT 0")
    _agregar_columna_si_falta(cursor, "proyectos", "creado_en", "TEXT")
    _agregar_columna_si_falta(cursor, "recursos", "empresa_id", "INTEGER")
    _agregar_columna_si_falta(cursor, "recursos", "codigo", "TEXT")
    _agregar_columna_si_falta(cursor, "recursos", "marca", "TEXT")
    cursor.execute("""CREATE UNIQUE INDEX IF NOT EXISTS idx_recursos_empresa_codigo
                      ON recursos(empresa_id, codigo)
                      WHERE codigo IS NOT NULL AND TRIM(codigo) <> ''""")
    cursor.execute("""CREATE INDEX IF NOT EXISTS idx_precios_recurso
                      ON proveedor_precios(empresa_id, recurso_id, fecha_precio DESC)""")

    # Control de la prueba gratuita (services/offline_license.py).
    cursor.execute("""CREATE TABLE IF NOT EXISTS control_prueba (
            id INTEGER PRIMARY KEY CHECK(id=1), inicio TEXT NOT NULL,
            ultimo_uso TEXT NOT NULL, codigo_equipo TEXT NOT NULL)""")


def _agregar_columna_si_falta(cursor, tabla, columna, definicion):
    columnas = {fila[1] for fila in cursor.execute(f"PRAGMA table_info({tabla})")}
    if columna not in columnas:
        cursor.execute(f"ALTER TABLE {tabla} ADD COLUMN {columna} {definicion}")
