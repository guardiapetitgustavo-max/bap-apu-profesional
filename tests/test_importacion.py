import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import database
from services.importacion_service import ejecutar_importacion, previsualizar_importacion


class ImportacionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db_path = str(Path(self.temp.name) / "importacion.db")
        self.patch = patch.object(database, "DB_PATH", self.db_path)
        self.patch.start(); database.crear_tablas()
        with database.conectar() as conn:
            self.empresa_id = conn.execute("SELECT id FROM empresas LIMIT 1").fetchone()[0]
            self.usuario_id = conn.execute("SELECT id FROM usuarios LIMIT 1").fetchone()[0]

    def tearDown(self):
        self.patch.stop(); self.temp.cleanup()

    def _csv(self):
        ruta = Path(self.temp.name) / "precios.csv"
        ruta.write_text(
            "Codigo_Recurso;Nombre_Recurso;Unidad;Tipo;Marca;Precio;Proveedor_RUC;Proveedor;Calidad_1_a_5;Stock;Plazo_Entrega_Dias;Fecha_Precio;Actualizar_Precio;URL_Fuente\n"
            "MAT-001;Cemento Tipo I;BOL;Material;Sol;30,90;20111111111;Proveedor Uno;5;100;1;2026-09-12;NO;https://uno.test\n"
            "MAT-001;Cemento Tipo I;BOL;Material;Sol;29,80;20222222222;Proveedor Dos;4;80;2;2026-09-12;SI;https://dos.test\n",
            encoding="utf-8",
        )
        return ruta

    def test_importa_recurso_dos_ofertas_y_actualiza_precio(self):
        ruta = self._csv()
        previa = previsualizar_importacion(ruta, self.empresa_id)
        self.assertEqual([f["accion"] for f in previa], ["CREAR", "OFERTA"])
        resultado = ejecutar_importacion(ruta, self.empresa_id, self.usuario_id)
        self.assertEqual(resultado["nuevos"], 1)
        self.assertEqual(resultado["ofertas"], 2)
        with database.conectar() as conn:
            recurso = conn.execute("SELECT id,precio FROM recursos WHERE codigo='MAT-001'").fetchone()
            self.assertEqual(recurso[1], 29.80)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM proveedor_precios WHERE recurso_id=?",(recurso[0],)).fetchone()[0],2)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM historial_precios WHERE recurso_id=?",(recurso[0],)).fetchone()[0],1)

    def test_rechaza_columnas_incompletas(self):
        ruta = Path(self.temp.name) / "malo.csv"
        ruta.write_text("Nombre_Recurso;Precio\nCemento;30\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Faltan columnas"):
            previsualizar_importacion(ruta, self.empresa_id)


if __name__ == "__main__":
    unittest.main()
