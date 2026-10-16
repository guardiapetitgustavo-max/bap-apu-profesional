import shutil
import sqlite3
from contextlib import closing
from pathlib import Path

import pytest

from bap_apu.data.migraciones.runner import ErrorMigracion
from bap_apu.services.apu import ApuService
from bap_apu.services.empresa import EmpresaService
from bap_apu.services.licencias import LicenciaService
from bap_apu.services.proyectos import ProyectosService
from bap_apu.services.respaldos import RespaldoService

FIXTURE = Path(__file__).parent / "fixtures" / "base_1_4_0_con_datos.db"


def _nombre(ruta, empresa_id=1):
    with closing(sqlite3.connect(ruta)) as conn:
        return conn.execute("SELECT nombre_comercial FROM empresas WHERE id=?", (empresa_id,)).fetchone()[0]


def _copia_modificada(db, destino, nombre, version=None):
    shutil.copy2(db.ruta, destino)
    with closing(sqlite3.connect(destino)) as conn:
        conn.execute("UPDATE empresas SET nombre_comercial=? WHERE id=1", (nombre,))
        if version is not None:
            conn.execute(f"PRAGMA user_version={version}")
        conn.commit()
    return destino


def test_crea_respaldo_con_hash(db, ctx_admin, tmp_path):
    carpeta = tmp_path / "backups"
    ruta, digest = RespaldoService(db, tmp_path).crear(ctx_admin, carpeta)
    assert Path(ruta).exists()
    assert len(digest) == 64
    with db.lectura() as conn:
        assert conn.execute("SELECT hash_sha256 FROM respaldos").fetchone()[0] == digest
        assert conn.execute("SELECT COUNT(*) FROM auditoria WHERE accion='RESPALDO_CREADO'").fetchone()[0] == 1


def test_restaura_y_conserva_emergencia(db, ctx_admin, tmp_path):
    respaldo = _copia_modificada(db, tmp_path / "respaldo.db", "Empresa restaurada")
    emergencia = Path(RespaldoService(db, tmp_path).restaurar(ctx_admin, respaldo))
    assert emergencia.is_file()
    assert _nombre(db.ruta) == "Empresa restaurada"


def test_rechaza_archivo_ajeno(db, ctx_admin, tmp_path):
    ajeno = tmp_path / "ajeno.db"
    with closing(sqlite3.connect(ajeno)) as conn:
        conn.execute("CREATE TABLE cualquiera(id INTEGER)")
        conn.commit()
    with pytest.raises(ValueError):
        RespaldoService(db, tmp_path).restaurar(ctx_admin, ajeno)


def test_restaurar_respaldo_1_4_0_lo_migra(db, ctx_admin, tmp_path):
    respaldo = tmp_path / "viejo.db"
    shutil.copy2(FIXTURE, respaldo)
    RespaldoService(db, tmp_path).restaurar(ctx_admin, respaldo)
    with closing(sqlite3.connect(db.ruta)) as conn:
        assert conn.execute("PRAGMA user_version").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM proyectos").fetchone()[0] == 2


def test_restaurar_tras_varias_operaciones(db, ctx_admin, tmp_path):
    proyecto_id = ProyectosService(db).crear(ctx_admin, "Obra de prueba")
    ApuService(db).total(ctx_admin, proyecto_id)
    ProyectosService(db).listar(ctx_admin)
    EmpresaService(db, LicenciaService(db, tmp_path)).obtener_dashboard(ctx_admin)
    respaldo = _copia_modificada(db, tmp_path / "otro.db", "Tras operaciones")
    RespaldoService(db, tmp_path).restaurar(ctx_admin, respaldo)
    assert _nombre(db.ruta) == "Tras operaciones"


def test_migracion_fallida_vuelve_a_emergencia(db, ctx_admin, tmp_path):
    antes = _nombre(db.ruta)
    respaldo = _copia_modificada(db, tmp_path / "futuro.db", "Futura", version=99)
    with pytest.raises(ErrorMigracion):
        RespaldoService(db, tmp_path).restaurar(ctx_admin, respaldo)
    assert _nombre(db.ruta) == antes


def test_restaurar_audita_con_usuario_nulo_si_no_existe_en_la_base_restaurada(db, ctx_admin, tmp_path):
    from dataclasses import replace
    ctx = replace(ctx_admin, usuario_id=999)
    respaldo = _copia_modificada(db, tmp_path / "otro.db", "Sin usuario")
    emergencia = RespaldoService(db, tmp_path).restaurar(ctx, respaldo)
    assert Path(emergencia).is_file()
    with db.lectura() as conn:
        filas = conn.execute(
            "SELECT usuario_id FROM auditoria WHERE accion='RESPALDO_RESTAURADO'").fetchall()
    assert filas == [(None,)]


def test_cualquier_fallo_al_preparar_vuelve_a_emergencia(db, ctx_admin, tmp_path, monkeypatch):
    antes = _nombre(db.ruta)
    respaldo = _copia_modificada(db, tmp_path / "otro.db", "Nueva")

    def falla(*args, **kwargs):
        raise sqlite3.OperationalError("disco lleno")

    monkeypatch.setattr("bap_apu.services.respaldos.preparar_base", falla)
    with pytest.raises(sqlite3.OperationalError):
        RespaldoService(db, tmp_path).restaurar(ctx_admin, respaldo)
    assert _nombre(db.ruta) == antes
