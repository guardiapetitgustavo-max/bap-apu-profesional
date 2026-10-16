"""Aplica las migraciones pendientes con un respaldo previo verificado."""
import sqlite3
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable

from bap_apu.data.migraciones import m0001_esquema_1_4_0 as m0001
from bap_apu.errores import ErrorMigracion


@dataclass(frozen=True)
class Migracion:
    version: int
    nombre: str
    aplicar: Callable


@dataclass(frozen=True)
class ResultadoMigracion:
    version_inicial: int
    version_final: int
    respaldo: Path | None


MIGRACIONES = (Migracion(1, "esquema_1_4_0", m0001.aplicar),)
VERSION_ESQUEMA = MIGRACIONES[-1].version


def respaldar_sqlite(origen: Path, destino: Path) -> Path:
    """Copia `origen` en `destino` con la API de respaldo y verifica la copia.

    Nunca toca un archivo existente: si `destino` ya existe, usa `nombre_1`,
    `nombre_2`, ... y devuelve la ruta realmente escrita.
    """
    destino = Path(destino)
    try:
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino = _reservar_nombre_libre(destino)
    except OSError as exc:
        raise ErrorMigracion(f"No se pudo crear el respaldo previo en {destino}: {exc}") from exc
    try:
        with closing(sqlite3.connect(origen)) as fuente, closing(sqlite3.connect(destino)) as copia:
            fuente.backup(copia)
            estado = copia.execute("PRAGMA integrity_check").fetchone()[0]
    except (OSError, sqlite3.Error) as exc:
        _borrar(destino)
        raise ErrorMigracion(f"No se pudo crear el respaldo previo en {destino}: {exc}") from exc
    if estado != "ok":
        _borrar(destino)
        raise ErrorMigracion(f"El respaldo previo en {destino} no superó la verificación de integridad: {estado}")
    return destino


def _reservar_nombre_libre(destino: Path) -> Path:
    """Crea en exclusiva un archivo vacío con el primer nombre libre y lo devuelve."""
    candidato, n = destino, 0
    while True:
        try:
            with open(candidato, "xb"):
                return candidato
        except FileExistsError:
            n += 1
            candidato = destino.with_name(f"{destino.stem}_{n}{destino.suffix}")


def _borrar(ruta: Path) -> None:
    try:
        if ruta.is_file():
            ruta.unlink()
    except OSError:
        pass


def _leer_estado(ruta: Path) -> tuple[int, int]:
    with closing(sqlite3.connect(ruta)) as conn:
        version = conn.execute("PRAGMA user_version").fetchone()[0]
        tablas = conn.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'").fetchone()[0]
    return version, tablas


def migrar(db, carpeta_respaldos: Path, migraciones=MIGRACIONES) -> ResultadoMigracion:
    v, tablas = _leer_estado(db.ruta)
    objetivo = migraciones[-1].version
    if v > objetivo:
        raise ErrorMigracion(
            "La base de datos fue creada con una versión más reciente de BAP APU Profesional. "
            "Actualice el programa."
        )
    if v == objetivo:
        return ResultadoMigracion(v, v, None)

    respaldo = None
    if tablas > 0:
        marca = datetime.now().strftime("%Y%m%d_%H%M%S")
        respaldo = respaldar_sqlite(db.ruta, Path(carpeta_respaldos) / f"pre_migracion_v{v}_{marca}.db")

    conn = sqlite3.connect(db.ruta, isolation_level=None)
    try:
        for m in migraciones:
            if m.version <= v:
                continue
            try:
                conn.execute("BEGIN IMMEDIATE")
                m.aplicar(conn)
                conn.execute(f"PRAGMA user_version = {int(m.version)}")
                conn.execute("COMMIT")
            except Exception as exc:
                if conn.in_transaction:
                    conn.execute("ROLLBACK")
                mensaje = f"No se pudo actualizar la base de datos (paso {m.version}: {m.nombre}): {exc}."
                if respaldo is not None:
                    mensaje += f" Sus datos están respaldados en: {respaldo}"
                raise ErrorMigracion(mensaje, respaldo) from exc
    finally:
        conn.close()
    return ResultadoMigracion(v, objetivo, respaldo)
