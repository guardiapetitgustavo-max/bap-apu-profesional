import shutil
from pathlib import Path

import pytest

from bap_apu.arranque import preparar_base
from bap_apu.contexto import Contexto
from bap_apu.data.db import Database
from bap_apu.data.repos import precios
from bap_apu.errores import ErrorValidacion, PermisoDenegado
from bap_apu.services.apu import ApuService
from bap_apu.services.partidas import PartidasService
from bap_apu.services.proyectos import ProyectosService
from bap_apu.services.recursos import RecursosService

FIXTURE_1_4_0 = Path(__file__).parent / "fixtures" / "base_1_4_0_con_datos.db"
AJENO = "El proyecto no existe o no pertenece a su empresa."


def _ctx_rol(db, ctx_admin, rol):
    with db.lectura() as conn:
        permisos = frozenset(f[0] for f in conn.execute(
            """SELECT p.codigo FROM rol_permisos rp
               JOIN permisos p ON p.id = rp.permiso_id
               JOIN roles r ON r.id = rp.rol_id WHERE r.nombre = ?""", (rol,)))
    return Contexto(usuario_id=97, usuario="consulta", nombre_completo=rol, rol=rol,
                    permisos=permisos, empresa_id=ctx_admin.empresa_id, token="t")


def _insertar_partida(db, detalle):
    with db.transaccion() as conn:
        partida_id = conn.execute(
            "INSERT INTO partidas (nombre, unidad, costo_referencia, fuente) VALUES (?, ?, ?, ?)",
            ("Partida prueba", "m2", 25.50, "prueba"),
        ).lastrowid
        for fila in detalle:
            conn.execute(
                """INSERT INTO partida_detalle
                   (partida_id, nombre, unidad, cantidad, precio, parcial, tipo)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""", (partida_id, *fila))
    return partida_id


# --- Casos portados de tests/test_database.py ---

def test_flujo_apu_y_totales(db, ctx_admin):
    proyectos, apu = ProyectosService(db), ApuService(db)
    proyecto_id = proyectos.crear(ctx_admin, "Proyecto prueba")
    assert proyectos.listar(ctx_admin)[0][0] == proyecto_id
    RecursosService(db).crear(ctx_admin, "Cemento", "BOL", 30, "Material")
    apu.agregar_item(ctx_admin, proyecto_id, "Cemento", "BOL", 30, 2, "Material")

    assert apu.total(ctx_admin, proyecto_id) == 60
    assert apu.subtotales(ctx_admin, proyecto_id)["Materiales"] == 60


def test_eliminar_proyecto_elimina_su_detalle(db, ctx_admin):
    proyectos, apu = ProyectosService(db), ApuService(db)
    proyecto_id = proyectos.crear(ctx_admin, "Temporal")
    apu.agregar_item(ctx_admin, proyecto_id, "Recurso", "UND", 10, 1, "Equipo")
    proyectos.eliminar(ctx_admin, proyecto_id)

    with db.lectura() as conn:
        assert conn.execute("SELECT COUNT(*) FROM detalle_apu WHERE proyecto_id=?",
                            (proyecto_id,)).fetchone()[0] == 0
    assert proyectos.listar(ctx_admin) == []


def test_cargar_partida_conserva_precio_y_parcial(db, ctx_admin):
    proyecto_id = ProyectosService(db).crear(ctx_admin, "Proyecto con partida")
    partida_id = _insertar_partida(db, [("Material prueba", "UND", 1.5, 17, 25.5, "Material")])

    cantidad = PartidasService(db).cargar_en_proyecto(ctx_admin, partida_id, proyecto_id)
    detalle = ApuService(db).detalle(ctx_admin, proyecto_id)
    assert cantidad == 1
    assert detalle[0][3] == 17
    assert detalle[0][5] == 25.5


# --- Casos nuevos ---

def test_partida_vacia_no_se_carga(db, ctx_admin):
    proyecto_id = ProyectosService(db).crear(ctx_admin, "Proyecto")
    partida_id = _insertar_partida(db, [])
    with pytest.raises(ErrorValidacion, match="La partida seleccionada no contiene recursos"):
        PartidasService(db).cargar_en_proyecto(ctx_admin, partida_id, proyecto_id)


def test_ids_de_otra_empresa_no_se_tocan(db, ctx_admin):
    with db.transaccion() as conn:
        otra = conn.execute("INSERT INTO empresas(razon_social, nombre_comercial) VALUES (?, ?)",
                            ("Otra Empresa SAC", "Otra")).lastrowid
        proyecto_ajeno = conn.execute("INSERT INTO proyectos(nombre, empresa_id) VALUES (?, ?)",
                                      ("Proyecto ajeno", otra)).lastrowid
        item_ajeno = conn.execute(
            """INSERT INTO detalle_apu (proyecto_id, nombre, unidad, precio, cantidad, parcial, tipo)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (proyecto_ajeno, "Arena", "M3", 50, 2, 100, "Material")).lastrowid
    partida_id = _insertar_partida(db, [("Material prueba", "UND", 1.5, 17, 25.5, "Material")])
    apu, proyectos, partidas = ApuService(db), ProyectosService(db), PartidasService(db)

    with pytest.raises(ErrorValidacion, match=AJENO):
        apu.eliminar_item(ctx_admin, item_ajeno)
    with pytest.raises(ErrorValidacion, match=AJENO):
        apu.detalle(ctx_admin, proyecto_ajeno)
    with pytest.raises(ErrorValidacion, match=AJENO):
        apu.total(ctx_admin, proyecto_ajeno)
    with pytest.raises(ErrorValidacion, match=AJENO):
        apu.limpiar(ctx_admin, proyecto_ajeno)
    with pytest.raises(ErrorValidacion, match=AJENO):
        apu.agregar_item(ctx_admin, proyecto_ajeno, "X", "UND", 1, 1, "Material")
    with pytest.raises(ErrorValidacion, match=AJENO):
        proyectos.eliminar(ctx_admin, proyecto_ajeno)
    with pytest.raises(ErrorValidacion, match=AJENO):
        partidas.cargar_en_proyecto(ctx_admin, partida_id, proyecto_ajeno)
    with pytest.raises(ErrorValidacion, match=AJENO):
        apu.eliminar_item(ctx_admin, 999999)

    with db.lectura() as conn:
        assert conn.execute("SELECT id, nombre, parcial FROM detalle_apu WHERE proyecto_id=?",
                            (proyecto_ajeno,)).fetchall() == [(item_ajeno, "Arena", 100)]
        assert conn.execute("SELECT nombre FROM proyectos WHERE id=?",
                            (proyecto_ajeno,)).fetchone() == ("Proyecto ajeno",)


def test_consulta_no_edita_apu(db, ctx_admin):
    proyecto_id = ProyectosService(db).crear(ctx_admin, "Proyecto")
    consulta = _ctx_rol(db, ctx_admin, "Consulta")
    apu = ApuService(db)
    assert apu.detalle(consulta, proyecto_id) == []
    with pytest.raises(PermisoDenegado):
        apu.agregar_item(consulta, proyecto_id, "Cemento", "BOL", 30, 2, "Material")
    with pytest.raises(PermisoDenegado):
        apu.limpiar(consulta, proyecto_id)
    assert apu.detalle(ctx_admin, proyecto_id) == []


def test_nombre_de_proyecto_obligatorio(ctx_admin, db):
    with pytest.raises(ErrorValidacion, match="El nombre del proyecto es obligatorio"):
        ProyectosService(db).crear(ctx_admin, "   ")


def test_aplicar_oferta_registra_historial(db, ctx_admin):
    recursos = RecursosService(db)
    recurso_id = recursos.crear(ctx_admin, "Cemento", "BOL", 30, "Material")
    with db.transaccion() as conn:
        proveedor_id = conn.execute("INSERT INTO proveedores(empresa_id, nombre) VALUES (?, ?)",
                                    (ctx_admin.empresa_id, "Ferretería Uno")).lastrowid
        precios.insertar_oferta(conn, ctx_admin.empresa_id, proveedor_id, recurso_id, "C-1",
                                "Cemento", "BOL", "Sol", 27.5, 4, 10, 2, "lista", "2026-10-01")
    ofertas = recursos.ofertas(ctx_admin, recurso_id)
    assert len(ofertas) == 1
    assert ofertas[0][1] == "Ferretería Uno"
    assert ofertas[0][3] == 27.5

    assert recursos.aplicar_oferta(ctx_admin, recurso_id, ofertas[0][0]) == 27.5

    with db.lectura() as conn:
        assert conn.execute("SELECT precio FROM recursos WHERE id=?", (recurso_id,)).fetchone()[0] == 27.5
        assert conn.execute(
            """SELECT empresa_id, recurso_id, proveedor_id, precio_anterior, precio_nuevo, origen
               FROM historial_precios""").fetchall() == [
            (ctx_admin.empresa_id, recurso_id, proveedor_id, 30, 27.5, "SELECCION_PROVEEDOR")]


def test_aplicar_oferta_inexistente(db, ctx_admin):
    recursos = RecursosService(db)
    recurso_id = recursos.crear(ctx_admin, "Cemento", "BOL", 30, "Material")
    with pytest.raises(ErrorValidacion, match="La oferta seleccionada no existe o ya no está activa."):
        recursos.aplicar_oferta(ctx_admin, recurso_id, 999)
    with db.lectura() as conn:
        assert conn.execute("SELECT COUNT(*) FROM historial_precios").fetchone()[0] == 0


def test_total_fixture_1_4_0(tmp_path, ctx_admin):
    copia = tmp_path / "copia.db"
    shutil.copyfile(FIXTURE_1_4_0, copia)
    base = Database(copia)
    preparar_base(base, tmp_path / "datos")
    with base.lectura() as conn:
        proyecto_id, empresa_id = conn.execute(
            "SELECT id, empresa_id FROM proyectos WHERE nombre=?", ("Vivienda Los Pinos",)).fetchone()
        esperado = conn.execute("SELECT SUM(parcial) FROM detalle_apu WHERE proyecto_id=?",
                                (proyecto_id,)).fetchone()[0]
    ctx = Contexto(usuario_id=1, usuario="admin", nombre_completo="Admin", rol="Administrador",
                   permisos=ctx_admin.permisos, empresa_id=empresa_id, token="t")
    apu = ApuService(base)

    assert apu.total(ctx, proyecto_id) == esperado
    subtotales = apu.subtotales(ctx, proyecto_id)
    assert "Herramientas" not in subtotales
    assert subtotales == {"Mano de Obra": 344, "Materiales": 420, "Equipo": 160}
