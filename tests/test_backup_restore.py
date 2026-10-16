import shutil
import sqlite3
import tempfile
from contextlib import closing
import unittest
from pathlib import Path
from unittest.mock import patch

import database
from services.business_service import restaurar_respaldo


class BackupRestoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Path(self.tmp.name) / "actual.db"
        shutil.copy2(Path(__file__).resolve().parents[1] / "data" / "apu_seed.db", self.db)
        self.parche = patch.object(database, "DB_PATH", str(self.db))
        self.parche.start()

    def tearDown(self):
        self.parche.stop()
        self.tmp.cleanup()

    def test_restaura_y_conserva_emergencia(self):
        respaldo = Path(self.tmp.name) / "respaldo.db"
        shutil.copy2(self.db, respaldo)
        with closing(sqlite3.connect(respaldo)) as conn:
            conn.execute("UPDATE empresas SET nombre_comercial='Empresa restaurada' WHERE id=1")
            conn.commit()
        emergencia = Path(restaurar_respaldo(1, respaldo))
        self.assertTrue(emergencia.is_file())
        with closing(sqlite3.connect(self.db)) as conn:
            nombre = conn.execute("SELECT nombre_comercial FROM empresas WHERE id=1").fetchone()[0]
        self.assertEqual(nombre, "Empresa restaurada")

    def test_rechaza_archivo_ajeno(self):
        ajeno = Path(self.tmp.name) / "ajeno.db"
        with closing(sqlite3.connect(ajeno)) as conn:
            conn.execute("CREATE TABLE cualquiera(id INTEGER)")
            conn.commit()
        with self.assertRaises(ValueError):
            restaurar_respaldo(1, ajeno)


if __name__ == "__main__":
    unittest.main()
