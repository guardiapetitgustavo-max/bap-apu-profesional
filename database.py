import os
import shutil
import sqlite3
import sys
from contextlib import contextmanager
from pathlib import Path


TABLAS_MINIMAS = {"empresas", "usuarios", "recursos", "partidas", "proyectos", "detalle_apu"}


def _es_base_apu_valida(ruta):
    ruta = Path(ruta)
    if not ruta.is_file():
        return False
    try:
        with sqlite3.connect(f"file:{ruta.resolve().as_posix()}?mode=ro", uri=True) as conn:
            if conn.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                return False
            tablas = {fila[0] for fila in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        return TABLAS_MINIMAS.issubset(tablas)
    except sqlite3.DatabaseError:
        return False


def _instalar_base_inicial(destino, plantilla, legado=None):
    """Crea una sola vez la base del cliente y nunca reemplaza sus datos."""
    destino = Path(destino)
    if destino.exists():
        return destino
    destino.parent.mkdir(parents=True, exist_ok=True)
    candidatos = [legado, plantilla]
    origen = next((Path(r) for r in candidatos if r and _es_base_apu_valida(r)), None)
    if origen is None:
        return destino
    temporal = destino.with_suffix(".db.instalando")
    shutil.copy2(origen, temporal)
    os.replace(temporal, destino)
    return destino


def _resolver_db_path():
    if not getattr(sys, "frozen", False):
        return str(Path(__file__).resolve().with_name("apu.db"))
    datos = Path(os.getenv("LOCALAPPDATA") or (Path.home() / "AppData" / "Local")) / "BAP_APU_Profesional"
    destino = datos / "apu.db"
    plantilla = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent)) / "data" / "apu_seed.db"
    legado = Path(sys.executable).resolve().parent / "apu.db"
    return str(_instalar_base_inicial(destino, plantilla, legado))


DB_PATH = _resolver_db_path()

def conectar():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 5000")
    return conn


@contextmanager
def conexion():
    """Abre una transacción y garantiza cierre/rollback ante errores."""
    conn = conectar()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def crear_tablas():
    conn = conectar()
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

    _sembrar_seguridad(cursor)
    _sembrar_empresa_y_planes(cursor)

    conn.commit()
    conn.close()
    print(f"✅ BASE DE DATOS LISTA: {DB_PATH}")


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
        from security.passwords import hash_password
        rol_id = cursor.execute("SELECT id FROM roles WHERE nombre = 'Administrador'").fetchone()[0]
        cursor.execute(
            """INSERT INTO usuarios
               (usuario, nombre_completo, password_hash, rol_id, debe_cambiar_password)
               VALUES (?, ?, ?, ?, 1)""",
            ("admin", "Administrador del sistema", hash_password("admin123"), rol_id),
        )


def _agregar_columna_si_falta(cursor, tabla, columna, definicion):
    columnas = {fila[1] for fila in cursor.execute(f"PRAGMA table_info({tabla})")}
    if columna not in columnas:
        cursor.execute(f"ALTER TABLE {tabla} ADD COLUMN {columna} {definicion}")


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

def insertar_proyecto(nombre, empresa_id=None):
    nombre = nombre.strip()
    if not nombre:
        raise ValueError("El nombre del proyecto es obligatorio")
    with conexion() as conn:
        conn.execute("INSERT INTO proyectos (nombre, empresa_id, creado_en) VALUES (?, ?, CURRENT_TIMESTAMP)", (nombre, empresa_id))

def obtener_proyectos(empresa_id=None):
    conn = conectar()
    cursor = conn.cursor()
    if empresa_id is None:
        cursor.execute("SELECT id, nombre FROM proyectos ORDER BY nombre COLLATE NOCASE")
    else:
        cursor.execute("SELECT id, nombre FROM proyectos WHERE empresa_id=? ORDER BY nombre COLLATE NOCASE", (empresa_id,))
    proyectos = cursor.fetchall()
    conn.close()
    return proyectos

def insertar_recurso(nombre, unidad, precio, tipo, empresa_id=None):
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO recursos (nombre, unidad, precio, tipo, empresa_id)
        VALUES (?, ?, ?, ?, ?)
    """, (nombre, unidad, precio, tipo, empresa_id))
    conn.commit()
    conn.close()

def obtener_recursos(empresa_id=None):
    conn = conectar()
    cursor = conn.cursor()
    if empresa_id is None:
        cursor.execute("SELECT id, nombre, unidad, precio, tipo FROM recursos ORDER BY nombre COLLATE NOCASE")
    else:
        cursor.execute("SELECT id, nombre, unidad, precio, tipo FROM recursos WHERE empresa_id=? ORDER BY nombre COLLATE NOCASE", (empresa_id,))
    recursos = cursor.fetchall()
    conn.close()
    return recursos


def obtener_ofertas_recurso(empresa_id, recurso_id):
    """Devuelve la última oferta registrada por proveedor para un recurso."""
    with conectar() as conn:
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


def aplicar_precio_oferta(empresa_id, recurso_id, oferta_id, origen="SELECCION_PROVEEDOR"):
    with conexion() as conn:
        oferta = conn.execute(
            """SELECT precio,proveedor_id FROM proveedor_precios
               WHERE id=? AND empresa_id=? AND recurso_id=? AND activo=1""",
            (oferta_id, empresa_id, recurso_id),
        ).fetchone()
        if not oferta:
            raise ValueError("La oferta seleccionada no existe o ya no está activa.")
        anterior = conn.execute(
            "SELECT precio FROM recursos WHERE id=? AND empresa_id=?", (recurso_id, empresa_id)
        ).fetchone()
        if not anterior:
            raise ValueError("El recurso seleccionado no existe.")
        conn.execute("UPDATE recursos SET precio=? WHERE id=?", (oferta[0], recurso_id))
        conn.execute(
            """INSERT INTO historial_precios
               (empresa_id,recurso_id,proveedor_id,precio_anterior,precio_nuevo,origen)
               VALUES (?,?,?,?,?,?)""",
            (empresa_id, recurso_id, oferta[1], anterior[0], oferta[0], origen),
        )
    return float(oferta[0])

def insertar_detalle(proyecto_id, nombre, unidad, precio, cantidad, tipo):
    parcial = round(float(precio) * float(cantidad), 2)
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO detalle_apu (proyecto_id, nombre, unidad, precio, cantidad, parcial, tipo)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (proyecto_id, nombre, unidad, precio, cantidad, parcial, tipo))
    conn.commit()
    conn.close()

def obtener_apu(proyecto_id):
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, nombre, unidad, precio, cantidad, parcial, tipo 
        FROM detalle_apu 
        WHERE proyecto_id = ?
    """, (proyecto_id,))
    detalles = cursor.fetchall()
    conn.close()
    return detalles

def obtener_subtotales(proyecto_id):
    """Suma los costos agrupados por tipo (Mano de Obra, Material, Equipo)."""
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT tipo, SUM(parcial)
        FROM detalle_apu
        WHERE proyecto_id = ?
        GROUP BY tipo
    """, (proyecto_id,))

    resultados = cursor.fetchall()
    conn.close()

    subtotales = {
        "Mano de Obra": 0,
        "Materiales": 0,
        "Equipo": 0
    }

    for tipo, total in resultados:
        if total is None:
            continue
        tipo_limpio = tipo.strip().capitalize()
        if tipo_limpio in ["Mano de obra", "Mano de Obra"]:
            subtotales["Mano de Obra"] = round(total, 2)
        elif tipo_limpio in ["Material", "Materiales"]:
            subtotales["Materiales"] = round(total, 2)
        elif tipo_limpio in ["Equipo", "Equipos"]:
            subtotales["Equipo"] = round(total, 2)

    return subtotales

def obtener_total(proyecto_id):
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("SELECT SUM(parcial) FROM detalle_apu WHERE proyecto_id = ?", (proyecto_id,))
    total = cursor.fetchone()[0]
    conn.close()
    return round(total, 2) if total is not None else 0.0


def obtener_partidas():
    with conectar() as conn:
        return conn.execute(
            """SELECT id, nombre, unidad, costo_referencia
               FROM partidas ORDER BY nombre COLLATE NOCASE"""
        ).fetchall()


def obtener_detalle_partida(partida_id):
    with conectar() as conn:
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


def cargar_partida_en_proyecto(partida_id, proyecto_id):
    """Copia una partida al proyecto conservando precios y cantidades del PDF."""
    detalle = obtener_detalle_partida(partida_id)
    if not detalle:
        raise ValueError("La partida seleccionada no contiene recursos")
    with conexion() as conn:
        conn.executemany(
            """INSERT INTO detalle_apu
               (proyecto_id, nombre, unidad, precio, cantidad, parcial, tipo)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            [
                (proyecto_id, item[1], item[2], item[5], item[4], item[6], item[7])
                for item in detalle
            ],
        )
    return len(detalle)

def eliminar_proyecto(proyecto_id):
    """Elimina el proyecto y su detalle APU en una sola transacción."""
    with conexion() as conn:
        conn.execute("DELETE FROM detalle_apu WHERE proyecto_id = ?", (proyecto_id,))
        conn.execute("DELETE FROM proyectos WHERE id = ?", (proyecto_id,))

def eliminar_detalle_apu(detalle_id):
    """Elimina un recurso específico asignado al APU por su ID."""
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM detalle_apu WHERE id = ?", (detalle_id,))
    conn.commit()
    conn.close()

def limpiar_todo_apu(proyecto_id):
    """Elimina absolutamente todo el desglose APU de un proyecto."""
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM detalle_apu WHERE proyecto_id = ?", (proyecto_id,))
    conn.commit()
    conn.close()

if __name__ == "__main__":
    crear_tablas()
