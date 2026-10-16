"""Preparación de la base al iniciar: migraciones y semillas."""
from pathlib import Path

from bap_apu.data.migraciones.runner import ResultadoMigracion, migrar
from bap_apu.data.semillas import sembrar


def preparar_base(db, carpeta_datos: Path) -> ResultadoMigracion:
    resultado = migrar(db, Path(carpeta_datos) / "respaldos")
    with db.transaccion() as conn:
        sembrar(conn)
    return resultado
