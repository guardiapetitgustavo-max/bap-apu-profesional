"""Instalación inicial de la base del cliente."""
import os
import shutil
import sqlite3
from contextlib import closing
from pathlib import Path

TABLAS_MINIMAS = {"empresas", "usuarios", "recursos", "partidas", "proyectos", "detalle_apu"}


def es_base_apu_valida(ruta) -> bool:
    ruta = Path(ruta)
    if not ruta.is_file():
        return False
    try:
        with closing(sqlite3.connect(f"file:{ruta.resolve().as_posix()}?mode=ro", uri=True)) as conn:
            if conn.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                return False
            tablas = {fila[0] for fila in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        return TABLAS_MINIMAS.issubset(tablas)
    except sqlite3.DatabaseError:
        return False


def instalar_base_inicial(destino, plantilla, legado=None) -> Path:
    """Crea una sola vez la base del cliente y nunca reemplaza sus datos."""
    destino = Path(destino)
    if destino.exists():
        return destino
    destino.parent.mkdir(parents=True, exist_ok=True)
    origen = next((Path(r) for r in (legado, plantilla) if r and es_base_apu_valida(r)), None)
    if origen is None:
        return destino
    temporal = destino.with_suffix(".db.instalando")
    shutil.copy2(origen, temporal)
    os.replace(temporal, destino)
    return destino
