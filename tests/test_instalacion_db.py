import sqlite3
import tempfile
import unittest
from pathlib import Path

import database


class InstalacionDBTests(unittest.TestCase):
    def _crear_base(self, ruta, marca):
        with sqlite3.connect(ruta) as conn:
            for tabla in database.TABLAS_MINIMAS:
                conn.execute(f"CREATE TABLE {tabla} (marca TEXT)")
                conn.execute(f"INSERT INTO {tabla}(marca) VALUES (?)", (marca,))

    def test_copia_plantilla_si_no_existe_base(self):
        with tempfile.TemporaryDirectory() as temporal:
            carpeta = Path(temporal)
            plantilla = carpeta / "seed.db"
            destino = carpeta / "cliente" / "apu.db"
            self._crear_base(plantilla, "SEMILLA")
            database._instalar_base_inicial(destino, plantilla)
            with sqlite3.connect(destino) as conn:
                self.assertEqual(conn.execute("SELECT marca FROM recursos").fetchone()[0], "SEMILLA")

    def test_no_sobrescribe_base_existente(self):
        with tempfile.TemporaryDirectory() as temporal:
            carpeta = Path(temporal)
            plantilla = carpeta / "seed.db"
            destino = carpeta / "apu.db"
            self._crear_base(plantilla, "SEMILLA")
            self._crear_base(destino, "CLIENTE")
            database._instalar_base_inicial(destino, plantilla)
            with sqlite3.connect(destino) as conn:
                self.assertEqual(conn.execute("SELECT marca FROM recursos").fetchone()[0], "CLIENTE")


if __name__ == "__main__":
    unittest.main()
