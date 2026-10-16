import sqlite3
import tempfile
from contextlib import closing
from pathlib import Path

import pytest

from bap_apu import brand, paths
from bap_apu.contexto import Contexto
from bap_apu.data import instalacion
from bap_apu.data.db import Database
from bap_apu.errores import ErrorValidacion, PermisoDenegado
from bap_apu.services.actualizaciones import _version


@pytest.fixture
def db(tmp_path):
    return Database(tmp_path / "t.db")


def test_version_1_5_0():
    assert brand.APP_VERSION == "1.5.0"
    assert brand.WHATSAPP == "+51 904 170 143"


def test_transaccion_hace_rollback_y_cierra(db):
    with db.transaccion() as c:
        c.execute("CREATE TABLE t(x)")
    capturada = None
    with pytest.raises(RuntimeError):
        with db.transaccion() as c:
            capturada = c
            c.execute("INSERT INTO t VALUES (1)")
            raise RuntimeError("fallo")
    with db.lectura() as c:
        assert c.execute("SELECT COUNT(*) FROM t").fetchone()[0] == 0
    with pytest.raises(sqlite3.ProgrammingError):
        capturada.execute("SELECT 1")


def test_lectura_cierra(db):
    with db.lectura() as c:
        pass
    with pytest.raises(sqlite3.ProgrammingError):
        c.execute("SELECT 1")


def test_foreign_keys_activas(db):
    conn = db.conectar()
    try:
        assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1
    finally:
        conn.close()


def test_contexto_exigir():
    ctx = Contexto(1, "u", "U Uno", "admin", frozenset({"apu.ver"}), 1, "tok")
    ctx.exigir("apu.ver")
    with pytest.raises(PermisoDenegado) as exc:
        ctx.exigir("apu.editar")
    assert isinstance(exc.value, PermissionError)
    assert "apu.editar" in str(exc.value)
    assert ctx.puede("apu.ver") and not ctx.puede("apu.editar")


def test_error_validacion_es_value_error():
    assert issubclass(ErrorValidacion, ValueError)
    with pytest.raises(ValueError):
        raise ErrorValidacion("x")


def _crear_base(ruta, marca):
    with closing(sqlite3.connect(ruta)) as conn:
        for tabla in instalacion.TABLAS_MINIMAS:
            conn.execute(f"CREATE TABLE {tabla} (marca TEXT)")
            conn.execute(f"INSERT INTO {tabla}(marca) VALUES (?)", (marca,))
        conn.commit()


def test_instalacion_no_sobrescribe():
    with tempfile.TemporaryDirectory() as temporal:
        carpeta = Path(temporal)
        plantilla = carpeta / "seed.db"
        _crear_base(plantilla, "SEMILLA")
        destino = carpeta / "cliente" / "apu.db"
        instalacion.instalar_base_inicial(destino, plantilla)
        with closing(sqlite3.connect(destino)) as conn:
            assert conn.execute("SELECT marca FROM recursos").fetchone()[0] == "SEMILLA"
        destino2 = carpeta / "apu.db"
        _crear_base(destino2, "CLIENTE")
        instalacion.instalar_base_inicial(destino2, plantilla)
        with closing(sqlite3.connect(destino2)) as conn:
            assert conn.execute("SELECT marca FROM recursos").fetchone()[0] == "CLIENTE"


def test_recurso_apunta_a_assets():
    assert paths.recurso("assets", "bap_isotipo.png").is_file()


def test_version_compara():
    assert _version("1.10.0") > _version("1.9.9")
    assert _version("x") == (0,)


def test_contexto_desde_sesion_lee_atributos():
    from types import SimpleNamespace
    sesion = SimpleNamespace(id=7, usuario="ana", nombre_completo="Ana Paz", rol="admin",
                             permisos=frozenset({"apu.ver", "apu.editar"}),
                             debe_cambiar_password=False, token="tok123")
    ctx = Contexto.desde_sesion(sesion, 3)
    assert ctx.usuario_id == 7
    assert ctx.usuario == "ana"
    assert ctx.nombre_completo == "Ana Paz"
    assert ctx.rol == "admin"
    assert ctx.permisos == frozenset({"apu.ver", "apu.editar"})
    assert ctx.empresa_id == 3
    assert ctx.token == "tok123"
