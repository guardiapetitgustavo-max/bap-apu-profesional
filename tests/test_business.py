import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import database
from services.business_service import empresa_principal, estado_licencia
from services.report_service import exportar_reporte_excel


class BusinessTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.db_path=str(Path(self.temp.name)/"business.db")
        self.patch=patch.object(database,"DB_PATH",self.db_path); self.patch.start(); database.crear_tablas()
        self.empresa=empresa_principal(1)

    def tearDown(self):self.patch.stop();self.temp.cleanup()

    def test_licencia_y_excel(self):
        self.assertEqual(estado_licencia(self.empresa[0])[0],"PRUEBA")
        excel=Path(self.temp.name)/"reporte.xlsx";exportar_reporte_excel(self.empresa[0],excel)
        self.assertTrue(excel.exists());self.assertGreater(excel.stat().st_size,4000)


if __name__=="__main__":unittest.main()
