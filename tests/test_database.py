import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import database


class DatabaseTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = str(Path(self.temp_dir.name) / "test_apu.db")
        self.path_patch = patch.object(database, "DB_PATH", self.db_path)
        self.path_patch.start()
        database.crear_tablas()

    def tearDown(self):
        self.path_patch.stop()
        self.temp_dir.cleanup()

    def test_flujo_apu_y_totales(self):
        database.insertar_proyecto("Proyecto prueba")
        proyecto_id = database.obtener_proyectos()[0][0]
        database.insertar_recurso("Cemento", "BOL", 30, "Material")
        database.insertar_detalle(proyecto_id, "Cemento", "BOL", 30, 2, "Material")

        self.assertEqual(database.obtener_total(proyecto_id), 60)
        self.assertEqual(database.obtener_subtotales(proyecto_id)["Materiales"], 60)

    def test_eliminar_proyecto_elimina_su_detalle(self):
        database.insertar_proyecto("Temporal")
        proyecto_id = database.obtener_proyectos()[0][0]
        database.insertar_detalle(proyecto_id, "Recurso", "UND", 10, 1, "Equipo")
        database.eliminar_proyecto(proyecto_id)

        self.assertEqual(database.obtener_apu(proyecto_id), [])
        self.assertEqual(database.obtener_proyectos(), [])

    def test_cargar_partida_conserva_precio_y_parcial(self):
        database.insertar_proyecto("Proyecto con partida")
        proyecto_id = database.obtener_proyectos()[0][0]
        with database.conexion() as conn:
            cursor = conn.execute(
                """INSERT INTO partidas
                   (nombre, unidad, costo_referencia, fuente)
                   VALUES (?, ?, ?, ?)""",
                ("Partida prueba", "m2", 25.50, "prueba"),
            )
            partida_id = cursor.lastrowid
            conn.execute(
                """INSERT INTO partida_detalle
                   (partida_id, nombre, unidad, cantidad, precio, parcial, tipo)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (partida_id, "Material prueba", "UND", 1.5, 17, 25.5, "Material"),
            )

        cantidad = database.cargar_partida_en_proyecto(partida_id, proyecto_id)
        detalle = database.obtener_apu(proyecto_id)
        self.assertEqual(cantidad, 1)
        self.assertEqual(detalle[0][3], 17)
        self.assertEqual(detalle[0][5], 25.5)


if __name__ == "__main__":
    unittest.main()
