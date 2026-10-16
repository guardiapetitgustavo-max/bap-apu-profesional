import hashlib
import shutil
import sqlite3
from contextlib import closing
from pathlib import Path

import pytest

from bap_apu.arranque import preparar_base
from bap_apu.data.db import Database
from bap_apu.data.migraciones.runner import MIGRACIONES, Migracion, migrar
from bap_apu.errores import ErrorMigracion

FIXTURE_1_4_0 = Path(__file__).parent / "fixtures" / "base_1_4_0_con_datos.db"
TABLAS_CON_DATOS = ("proyectos", "detalle_apu", "recursos", "usuarios", "proveedor_precios", "historial_precios")


def _copiar_fixture(tmp_path) -> Path:
    destino = tmp_path / "apu.db"
    shutil.copyfile(FIXTURE_1_4_0, destino)
    return destino


def _user_version(ruta) -> int:
    with closing(sqlite3.connect(ruta)) as conn:
        return conn.execute("PRAGMA user_version").fetchone()[0]


def _tablas(ruta) -> set[str]:
    with closing(sqlite3.connect(ruta)) as conn:
        return {fila[0] for fila in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}


def _conteos(ruta) -> dict[str, int]:
    with closing(sqlite3.connect(ruta)) as conn:
        return {t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in TABLAS_CON_DATOS}


def _sha256(ruta) -> str:
    return hashlib.sha256(Path(ruta).read_bytes()).hexdigest()


def test_base_nueva_queda_en_v1_sin_respaldo(tmp_path):
    db = Database(tmp_path / "apu.db")
    resultado = preparar_base(db, tmp_path)
    assert (resultado.version_inicial, resultado.version_final, resultado.respaldo) == (0, 1, None)
    assert {"empresas", "usuarios", "detalle_apu", "control_prueba"} <= _tablas(db.ruta)
    assert _user_version(db.ruta) == 1


def test_base_1_4_0_migra_con_respaldo_y_conserva_datos(tmp_path):
    ruta = _copiar_fixture(tmp_path)
    antes = _conteos(ruta)
    resultado = preparar_base(Database(ruta), tmp_path)
    assert _user_version(ruta) == 1
    assert resultado.version_inicial == 0 and resultado.version_final == 1
    assert resultado.respaldo is not None and resultado.respaldo.is_file()
    assert resultado.respaldo.parent == tmp_path / "respaldos"
    assert _conteos(ruta) == antes
    assert _conteos(resultado.respaldo) == antes


def test_esquema_equivalente_a_1_4_0(tmp_path):
    nueva = Database(tmp_path / "nueva" / "apu.db")
    nueva.ruta.parent.mkdir()
    preparar_base(nueva, tmp_path / "nueva")
    with closing(sqlite3.connect(FIXTURE_1_4_0)) as vieja, closing(sqlite3.connect(nueva.ruta)) as conn:
        tablas = [f[0] for f in vieja.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name <> 'sqlite_sequence'")]
        assert tablas
        for tabla in tablas:
            columnas_viejas = {f[1] for f in vieja.execute(f"PRAGMA table_info({tabla})")}
            columnas_nuevas = {f[1] for f in conn.execute(f"PRAGMA table_info({tabla})")}
            assert columnas_nuevas == columnas_viejas, tabla


def test_segunda_ejecucion_no_respalda(tmp_path):
    ruta = _copiar_fixture(tmp_path)
    db = Database(ruta)
    primero = migrar(db, tmp_path / "respaldos")
    assert primero.respaldo is not None
    segundo = migrar(db, tmp_path / "respaldos")
    assert segundo.respaldo is None
    assert (segundo.version_inicial, segundo.version_final) == (1, 1)


def test_semillas_idempotentes(tmp_path):
    db = Database(tmp_path / "apu.db")
    preparar_base(db, tmp_path)
    with closing(sqlite3.connect(db.ruta)) as conn:
        permisos_antes = conn.execute("SELECT COUNT(*) FROM rol_permisos").fetchone()[0]
    preparar_base(db, tmp_path)
    with closing(sqlite3.connect(db.ruta)) as conn:
        assert conn.execute("SELECT COUNT(*) FROM usuarios WHERE usuario='admin'").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM rol_permisos").fetchone()[0] == permisos_antes
    assert permisos_antes > 0


def test_falla_hace_rollback(tmp_path):
    db = Database(tmp_path / "apu.db")
    preparar_base(db, tmp_path)

    def rota(conn):
        conn.execute("CREATE TABLE x (id INTEGER)")
        raise RuntimeError("falla simulada")

    migraciones = MIGRACIONES + (Migracion(2, "rota", rota),)
    with pytest.raises(ErrorMigracion) as info:
        migrar(db, tmp_path / "respaldos", migraciones)
    assert info.value.respaldo is not None and info.value.respaldo.is_file()
    assert "paso 2: rota" in str(info.value)
    assert _user_version(db.ruta) == 1
    assert "x" not in _tablas(db.ruta)


def test_rechaza_base_mas_nueva(tmp_path):
    ruta = _copiar_fixture(tmp_path)
    with closing(sqlite3.connect(ruta)) as conn:
        conn.execute("PRAGMA user_version = 99")
    hash_antes = _sha256(ruta)
    with pytest.raises(ErrorMigracion, match="versión más reciente"):
        migrar(Database(ruta), tmp_path / "respaldos")
    assert _sha256(ruta) == hash_antes
    assert not (tmp_path / "respaldos").exists()


def test_sin_respaldo_no_migra(tmp_path):
    ruta = _copiar_fixture(tmp_path)
    archivo = tmp_path / "no_es_carpeta"
    archivo.write_text("x")
    with pytest.raises(ErrorMigracion):
        migrar(Database(ruta), archivo)
    assert _user_version(ruta) == 0
    assert "control_prueba" not in _tablas(ruta)


def test_fixtures_db_y_ctx_admin(db, ctx_admin):
    assert _user_version(db.ruta) == 1
    assert ctx_admin.usuario_id == 1 and ctx_admin.usuario == "admin"
    assert ctx_admin.rol == "Administrador"
    assert ctx_admin.puede("usuarios.gestionar") and len(ctx_admin.permisos) == 22
    with db.lectura() as conn:
        assert conn.execute("SELECT COUNT(*) FROM empresas WHERE id=?", (ctx_admin.empresa_id,)).fetchone()[0] == 1


def test_falla_sin_respaldo_no_menciona_none(tmp_path):
    db = Database(tmp_path / "apu.db")

    def rota(conn):
        raise RuntimeError("falla simulada")

    migraciones = MIGRACIONES + (Migracion(2, "rota", rota),)
    with pytest.raises(ErrorMigracion) as info:
        migrar(db, tmp_path / "respaldos", migraciones)
    assert info.value.respaldo is None
    assert "None" not in str(info.value)
    assert "paso 2: rota" in str(info.value)
    assert _user_version(db.ruta) == 1


def test_respaldo_no_sobrescribe_destino_existente(tmp_path):
    from bap_apu.data.migraciones.runner import respaldar_sqlite

    origen = _copiar_fixture(tmp_path)
    destino = tmp_path / "respaldos" / "pre_migracion_v0_20261016_120000.db"
    destino.parent.mkdir()
    destino.write_bytes(b"respaldo anterior valido")
    escrito = respaldar_sqlite(origen, destino)
    assert destino.read_bytes() == b"respaldo anterior valido"
    assert escrito != destino
    assert escrito == destino.with_name("pre_migracion_v0_20261016_120000_1.db")
    assert _conteos(escrito) == _conteos(origen)
