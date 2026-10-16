"""Genera una base de datos real de la versión 1.4.0 con datos de ejemplo.

Uso:  python tests/fixtures/crear_base_1_4_0.py <salida.db>

La base `base_1_4_0_con_datos.db` se generó con el commit `71fd64f` (código
1.4.0, `database.py` en la raíz del repositorio). Para regenerarla hay que usar
un worktree de ese commit (`git worktree add <carpeta> 71fd64f`) y ejecutar
este script desde allí, porque el código actual ya no contiene el esquema
1.4.0. Solo escribe en la ruta de salida indicada.
"""
import sqlite3
import sys
from contextlib import closing
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")  # el código legado imprime un emoji
RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ))

import database  # noqa: E402  (código legado 1.4.0)
from security.passwords import hash_password  # noqa: E402


def crear(salida):
    salida = Path(salida).resolve()
    if salida.exists():
        salida.unlink()
    salida.parent.mkdir(parents=True, exist_ok=True)
    database.DB_PATH = str(salida)
    database.crear_tablas()

    with closing(sqlite3.connect(salida)) as conn:
        rol_consulta = conn.execute("SELECT id FROM roles WHERE nombre='Consulta'").fetchone()[0]
        conn.execute(
            """INSERT INTO usuarios(usuario, nombre_completo, password_hash, rol_id, debe_cambiar_password)
               VALUES (?,?,?,?,0)""",
            ("lector", "Usuario de Consulta", hash_password("lector123"), rol_consulta),
        )
        conn.execute(
            "INSERT INTO usuario_empresa(usuario_id, empresa_id, es_principal) "
            "SELECT id, 1, 1 FROM usuarios WHERE usuario='lector'"
        )

        conn.execute(
            "INSERT INTO clientes(empresa_id, tipo_documento, numero_documento, nombre, email) "
            "VALUES (1,'RUC','20123456789','Constructora Andina SAC','contacto@andina.example')"
        )
        conn.execute(
            "INSERT INTO proveedores(empresa_id, ruc, nombre, contacto) "
            "VALUES (1,'20987654321','Ferretería Central SAC','Ana Pérez')"
        )

        pinos = conn.execute(
            "INSERT INTO proyectos(nombre, empresa_id, creado_en) VALUES ('Vivienda Los Pinos',1,CURRENT_TIMESTAMP)"
        ).lastrowid
        losa = conn.execute(
            "INSERT INTO proyectos(nombre, empresa_id, creado_en) VALUES ('Losa deportiva',1,CURRENT_TIMESTAMP)"
        ).lastrowid

        detalle = [
            (pinos, "Operario", "hh", 25.0, 8.0, 200.0, "Mano de Obra"),
            (pinos, "Peón", "hh", 18.0, 8.0, 144.0, "mano de obra "),
            (pinos, "Cemento Portland", "bol", 30.0, 10.0, 300.0, "Materiales"),
            (pinos, "Arena gruesa", "m3", 60.0, 2.0, 120.0, "Material"),
            (pinos, "Mezcladora", "hm", 40.0, 4.0, 160.0, "Equipos"),
            (pinos, "Herramientas manuales", "glb", 5.0, 3.0, 15.0, "Herramientas"),
            (losa, "Operario", "hh", 25.0, 6.0, 150.0, "Mano de Obra"),
            (losa, "Concreto premezclado", "m3", 280.0, 1.5, 420.0, "Materiales"),
            (losa, "Vibradora", "hm", 35.0, 2.0, 70.0, "Equipos"),
        ]
        conn.executemany(
            "INSERT INTO detalle_apu(proyecto_id,nombre,unidad,precio,cantidad,parcial,tipo) VALUES (?,?,?,?,?,?,?)",
            detalle,
        )

        recurso = conn.execute(
            "INSERT INTO recursos(nombre,unidad,precio,tipo,empresa_id) "
            "VALUES ('Cemento Portland','bol',30.0,'Materiales',1)"
        ).lastrowid
        proveedor = conn.execute("SELECT id FROM proveedores LIMIT 1").fetchone()[0]
        conn.execute(
            """INSERT INTO proveedor_precios(empresa_id,proveedor_id,recurso_id,unidad,precio,fecha_precio)
               VALUES (1,?,?,'bol',29.5,'2026-01-15')""",
            (proveedor, recurso),
        )
        conn.execute(
            """INSERT INTO historial_precios(empresa_id,recurso_id,proveedor_id,precio_anterior,precio_nuevo,origen)
               VALUES (1,?,?,28.0,29.5,'importacion')""",
            (recurso, proveedor),
        )
        conn.commit()
        assert conn.execute("PRAGMA user_version").fetchone()[0] == 0
    return salida


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Uso: python tests/fixtures/crear_base_1_4_0.py <salida.db>")
    print(crear(sys.argv[1]))
