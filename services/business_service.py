import hashlib
import os
import shutil
import sqlite3
from datetime import date, datetime
from pathlib import Path

import database
from database import conectar, conexion


def empresa_principal(usuario_id):
    with conectar() as conn:
        return conn.execute(
            """SELECT e.id,e.ruc,e.razon_social,e.nombre_comercial,e.direccion,e.telefono,e.email,e.moneda
               FROM empresas e JOIN usuario_empresa ue ON ue.empresa_id=e.id
               WHERE ue.usuario_id=? AND e.activo=1
               ORDER BY ue.es_principal DESC,e.id LIMIT 1""", (usuario_id,)
        ).fetchone()


def guardar_empresa(actor_id, empresa_id, ruc, razon_social, nombre_comercial, direccion, telefono, email):
    if not razon_social.strip(): raise ValueError("La razón social es obligatoria.")
    with conexion() as conn:
        conn.execute(
            """UPDATE empresas SET ruc=?,razon_social=?,nombre_comercial=?,direccion=?,telefono=?,email=?
               WHERE id=?""",
            (ruc.strip(),razon_social.strip(),nombre_comercial.strip(),direccion.strip(),telefono.strip(),email.strip(),empresa_id),
        )
        _auditar(conn,actor_id,"EMPRESA_ACTUALIZADA","empresas",str(empresa_id))


def listar_clientes(empresa_id):
    with conectar() as conn:
        return conn.execute(
            """SELECT id,tipo_documento,numero_documento,nombre,direccion,telefono,email,activo
               FROM clientes WHERE empresa_id=? ORDER BY nombre COLLATE NOCASE""", (empresa_id,)
        ).fetchall()


def crear_cliente(actor_id,empresa_id,tipo,numero,nombre,direccion,telefono,email):
    if not nombre.strip(): raise ValueError("El nombre del cliente es obligatorio.")
    with conexion() as conn:
        conn.execute(
            """INSERT INTO clientes(empresa_id,tipo_documento,numero_documento,nombre,direccion,telefono,email)
               VALUES (?,?,?,?,?,?,?)""",
            (empresa_id,tipo,numero.strip() or None,nombre.strip(),direccion.strip(),telefono.strip(),email.strip()),
        )
        _auditar(conn,actor_id,"CLIENTE_CREADO","clientes",nombre.strip())


def listar_proveedores(empresa_id):
    with conectar() as conn:
        return conn.execute(
            """SELECT id,ruc,nombre,contacto,telefono,email,activo FROM proveedores
               WHERE empresa_id=? ORDER BY nombre COLLATE NOCASE""", (empresa_id,)
        ).fetchall()


def crear_proveedor(actor_id,empresa_id,ruc,nombre,contacto,telefono,email):
    if not nombre.strip(): raise ValueError("El nombre del proveedor es obligatorio.")
    with conexion() as conn:
        conn.execute(
            """INSERT INTO proveedores(empresa_id,ruc,nombre,contacto,telefono,email)
               VALUES (?,?,?,?,?,?)""",
            (empresa_id,ruc.strip() or None,nombre.strip(),contacto.strip(),telefono.strip(),email.strip()),
        )
        _auditar(conn,actor_id,"PROVEEDOR_CREADO","proveedores",nombre.strip())


def obtener_dashboard(empresa_id):
    with conectar() as conn:
        proyectos=conn.execute("SELECT COUNT(*) FROM proyectos WHERE empresa_id=?",(empresa_id,)).fetchone()[0]
        clientes=conn.execute("SELECT COUNT(*) FROM clientes WHERE empresa_id=? AND activo=1",(empresa_id,)).fetchone()[0]
        recursos=conn.execute("SELECT COUNT(*) FROM recursos WHERE empresa_id=?",(empresa_id,)).fetchone()[0]
        partidas=conn.execute("SELECT COUNT(*) FROM partidas").fetchone()[0]
        total=conn.execute(
            """SELECT COALESCE(SUM(d.parcial),0) FROM detalle_apu d
               JOIN proyectos p ON p.id=d.proyecto_id WHERE p.empresa_id=?""",(empresa_id,)
        ).fetchone()[0]
        ultimos=conn.execute(
            """SELECT p.nombre,COALESCE(SUM(d.parcial),0) total FROM proyectos p
               LEFT JOIN detalle_apu d ON d.proyecto_id=p.id WHERE p.empresa_id=?
               GROUP BY p.id,p.nombre ORDER BY p.id DESC LIMIT 6""",(empresa_id,)
        ).fetchall()
        return {"proyectos":proyectos,"clientes":clientes,"recursos":recursos,"partidas":partidas,"total":total,"ultimos":ultimos}


def listar_auditoria(limite=300):
    with conectar() as conn:
        return conn.execute(
            """SELECT a.fecha,COALESCE(u.usuario,'SISTEMA'),a.accion,COALESCE(a.entidad,''),COALESCE(a.detalle,'')
               FROM auditoria a LEFT JOIN usuarios u ON u.id=a.usuario_id
               ORDER BY a.id DESC LIMIT ?""",(limite,)
        ).fetchall()


def estado_licencia(empresa_id):
    from services.offline_license import verificar_acceso
    estado = verificar_acceso()
    hoy = date.today().isoformat()
    vence = estado.vencimiento or "Fin de prueba en 15 días"
    plan = "BAP APU Profesional - hasta 5 equipos / 5 usuarios" if estado.modo == "LICENCIA" else "Prueba gratuita BAP"
    return (estado.modo, hoy, vence, plan, estado.max_usuarios, None, 0.0)


def crear_respaldo(actor_id,destino):
    destino=Path(destino)
    destino.mkdir(parents=True,exist_ok=True)
    archivo=destino/f"APU_backup_{datetime.now():%Y%m%d_%H%M%S}.db"
    shutil.copy2(database.DB_PATH,archivo)
    digest=hashlib.sha256(archivo.read_bytes()).hexdigest()
    with conexion() as conn:
        conn.execute(
            "INSERT INTO respaldos(usuario_id,ruta,hash_sha256,tamano) VALUES (?,?,?,?)",
            (actor_id,str(archivo),digest,archivo.stat().st_size),
        )
        _auditar(conn,actor_id,"RESPALDO_CREADO","respaldos",archivo.name)
    return str(archivo),digest


def restaurar_respaldo(actor_id, ruta_respaldo):
    """Valida y restaura un respaldo SQLite, conservando una copia de emergencia."""
    origen = Path(ruta_respaldo).resolve()
    if not origen.is_file():
        raise ValueError("El archivo de respaldo no existe.")
    if origen.suffix.lower() != ".db":
        raise ValueError("Seleccione un respaldo con extensión .db.")

    requeridas = {"empresas", "usuarios", "proyectos", "recursos", "detalle_apu"}
    try:
        with sqlite3.connect(f"file:{origen.as_posix()}?mode=ro", uri=True) as prueba:
            integridad = prueba.execute("PRAGMA integrity_check").fetchone()[0]
            tablas = {fila[0] for fila in prueba.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    except sqlite3.DatabaseError as exc:
        raise ValueError("El archivo seleccionado no es una base de datos válida.") from exc
    if integridad != "ok":
        raise ValueError("El respaldo está dañado y no puede restaurarse.")
    faltantes = requeridas - tablas
    if faltantes:
        raise ValueError("El archivo no corresponde a BAP APU Profesional.")

    destino = Path(database.DB_PATH).resolve()
    emergencia = destino.with_name(f"BAP_APU_emergencia_{datetime.now():%Y%m%d_%H%M%S}.db")
    temporal = destino.with_name(destino.name + ".restaurando")
    shutil.copy2(destino, emergencia)
    try:
        shutil.copy2(origen, temporal)
        os.replace(temporal, destino)
    except Exception:
        temporal.unlink(missing_ok=True)
        if emergencia.exists():
            shutil.copy2(emergencia, destino)
        raise
    return str(emergencia)


def obtener_configuracion(empresa_id):
    with conectar() as conn:
        return dict(conn.execute("SELECT clave,valor FROM configuracion WHERE empresa_id=?",(empresa_id,)).fetchall())


def guardar_configuracion(actor_id,empresa_id,valores):
    with conexion() as conn:
        for clave,valor in valores.items():
            conn.execute(
                """INSERT INTO configuracion(empresa_id,clave,valor) VALUES (?,?,?)
                   ON CONFLICT(empresa_id,clave) DO UPDATE SET valor=excluded.valor""",
                (empresa_id,clave,str(valor)),
            )
        _auditar(conn,actor_id,"CONFIGURACION_ACTUALIZADA","configuracion",str(empresa_id))


def _auditar(conn,usuario_id,accion,entidad,detalle):
    conn.execute(
        "INSERT INTO auditoria(usuario_id,accion,entidad,detalle) VALUES (?,?,?,?)",
        (usuario_id,accion,entidad,detalle),
    )
