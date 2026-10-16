"""Creación y restauración de respaldos de la base."""
import hashlib
import os
import shutil
import sqlite3
from contextlib import closing
from datetime import datetime
from pathlib import Path

from bap_apu.arranque import preparar_base
from bap_apu.contexto import Contexto
from bap_apu.data.db import Database
from bap_apu.data.migraciones.runner import ErrorMigracion, respaldar_sqlite
from bap_apu.data.repos import auditoria, respaldos
from bap_apu.errores import ErrorValidacion

TABLAS_REQUERIDAS = {"empresas", "usuarios", "proyectos", "recursos", "detalle_apu"}


class RespaldoService:
    def __init__(self, db: Database, carpeta_datos: Path):
        self._db = db
        self._carpeta_datos = Path(carpeta_datos)

    def crear(self, ctx: Contexto, destino) -> tuple[str, str]:
        ctx.exigir("respaldos.gestionar")
        archivo = respaldar_sqlite(
            Path(self._db.ruta), Path(destino) / f"APU_backup_{datetime.now():%Y%m%d_%H%M%S}.db")
        digest = hashlib.sha256(archivo.read_bytes()).hexdigest()
        with self._db.transaccion() as conn:
            respaldos.registrar(conn, ctx.usuario_id, archivo, digest, archivo.stat().st_size)
            auditoria.registrar(conn, ctx.usuario_id, "RESPALDO_CREADO", "respaldos", archivo.name)
        return str(archivo), digest

    def restaurar(self, ctx: Contexto, ruta) -> str:
        """Valida y restaura un respaldo, migrándolo; conserva una copia de emergencia."""
        ctx.exigir("respaldos.gestionar")
        origen = Path(ruta).resolve()
        _validar_respaldo(origen)

        destino = Path(self._db.ruta).resolve()
        emergencia = respaldar_sqlite(
            destino, destino.with_name(f"BAP_APU_emergencia_{datetime.now():%Y%m%d_%H%M%S}.db"))
        temporal = destino.with_name(destino.name + ".restaurando")
        try:
            shutil.copy2(origen, temporal)
            os.replace(temporal, destino)
        except Exception:
            temporal.unlink(missing_ok=True)
            shutil.copy2(emergencia, destino)
            raise
        try:
            preparar_base(self._db, self._carpeta_datos)
        except ErrorMigracion:
            shutil.copy2(emergencia, destino)
            raise
        with self._db.transaccion() as conn:
            auditoria.registrar(conn, ctx.usuario_id, "RESPALDO_RESTAURADO", "respaldos", origen.name)
        return str(emergencia)


def _validar_respaldo(origen: Path) -> None:
    if not origen.is_file():
        raise ErrorValidacion("El archivo de respaldo no existe.")
    if origen.suffix.lower() != ".db":
        raise ErrorValidacion("Seleccione un respaldo con extensión .db.")
    try:
        with closing(sqlite3.connect(f"file:{origen.as_posix()}?mode=ro", uri=True)) as prueba:
            integridad = prueba.execute("PRAGMA integrity_check").fetchone()[0]
            tablas = {fila[0] for fila in prueba.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    except sqlite3.DatabaseError as exc:
        raise ErrorValidacion("El archivo seleccionado no es una base de datos válida.") from exc
    if integridad != "ok":
        raise ErrorValidacion("El respaldo está dañado y no puede restaurarse.")
    if TABLAS_REQUERIDAS - tablas:
        raise ErrorValidacion("El archivo no corresponde a BAP APU Profesional.")
