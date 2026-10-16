"""Rutas de recursos y de datos del usuario."""
import os
import sys
from pathlib import Path

from bap_apu.data.instalacion import instalar_base_inicial


def raiz_recursos() -> Path:
    base = getattr(sys, "_MEIPASS", None)
    return Path(base) if base else Path(__file__).resolve().parents[1]


def recurso(*partes: str) -> Path:
    return raiz_recursos().joinpath(*partes)


def carpeta_datos() -> Path:
    if sys.platform == "win32":
        base = os.getenv("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
    else:
        base = os.getenv("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
    ruta = Path(base) / "BAP_APU_Profesional"
    ruta.mkdir(parents=True, exist_ok=True)
    return ruta


def ruta_base_datos() -> Path:
    """Ruta de apu.db; no se debe llamar al importar módulos."""
    if not getattr(sys, "frozen", False):
        return Path(__file__).resolve().parents[1] / "apu.db"
    destino = carpeta_datos() / "apu.db"
    plantilla = recurso("data", "apu_seed.db")
    legado = Path(sys.executable).resolve().parent / "apu.db"
    return instalar_base_inicial(destino, plantilla, legado)
