import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import database
from services.business_service import (
    crear_cliente, crear_proveedor, crear_respaldo, empresa_principal,
    estado_licencia, listar_clientes, listar_proveedores, obtener_dashboard,
)
from services.report_service import exportar_reporte_excel


class BusinessTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.db_path=str(Path(self.temp.name)/"business.db")
        self.patch=patch.object(database,"DB_PATH",self.db_path); self.patch.start(); database.crear_tablas()
        self.empresa=empresa_principal(1)

    def tearDown(self):self.patch.stop();self.temp.cleanup()

    def test_empresa_clientes_proveedores_dashboard(self):
        crear_cliente(1,self.empresa[0],"RUC","20123456789","Cliente Uno","Lima","999","cliente@test.pe")
        crear_proveedor(1,self.empresa[0],"20987654321","Proveedor Uno","Ana","988","proveedor@test.pe")
        database.insertar_proyecto("Proyecto Empresa",self.empresa[0])
        database.insertar_recurso("Recurso Empresa","UND",25,"Material",self.empresa[0])
        self.assertEqual(len(listar_clientes(self.empresa[0])),1)
        self.assertEqual(len(listar_proveedores(self.empresa[0])),1)
        datos=obtener_dashboard(self.empresa[0]);self.assertEqual(datos["proyectos"],1);self.assertEqual(datos["clientes"],1)

    def test_licencia_respaldo_y_excel(self):
        self.assertEqual(estado_licencia(self.empresa[0])[0],"PRUEBA")
        carpeta=Path(self.temp.name)/"backups";ruta,digest=crear_respaldo(1,carpeta)
        self.assertTrue(Path(ruta).exists());self.assertEqual(len(digest),64)
        excel=Path(self.temp.name)/"reporte.xlsx";exportar_reporte_excel(self.empresa[0],excel)
        self.assertTrue(excel.exists());self.assertGreater(excel.stat().st_size,4000)


if __name__=="__main__":unittest.main()
