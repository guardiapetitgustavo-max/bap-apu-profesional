import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import database
from security.passwords import hash_password, validar_fortaleza, verify_password
from services.auth_service import (
    autenticar,
    cambiar_password,
    cerrar_sesion,
    crear_usuario,
    listar_roles,
)


class AuthTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = str(Path(self.temp_dir.name) / "auth.db")
        self.path_patch = patch.object(database, "DB_PATH", self.db_path)
        self.path_patch.start()
        database.crear_tablas()

    def tearDown(self):
        self.path_patch.stop()
        self.temp_dir.cleanup()

    def test_hash_no_guarda_password_y_verifica(self):
        encoded = hash_password("ClaveSegura1")
        self.assertNotIn("ClaveSegura1", encoded)
        self.assertTrue(verify_password("ClaveSegura1", encoded))
        self.assertFalse(verify_password("Incorrecta1", encoded))

    def test_login_cambio_obligatorio_y_cierre(self):
        sesion, error = autenticar("admin", "admin123")
        self.assertIsNone(error)
        self.assertTrue(sesion.debe_cambiar_password)
        self.assertTrue(sesion.puede("usuarios.gestionar"))
        cambiar_password(sesion.id, "admin123", "AdminNueva1")
        cerrar_sesion(sesion)
        nueva_sesion, error = autenticar("admin", "AdminNueva1")
        self.assertIsNone(error)
        self.assertFalse(nueva_sesion.debe_cambiar_password)

    def test_usuario_consulta_recibe_permisos_limitados(self):
        rol_consulta = next(rol_id for rol_id, nombre in listar_roles() if nombre == "Consulta")
        crear_usuario(1, "lector", "Usuario Lector", "Lectura123", rol_consulta)
        sesion, error = autenticar("lector", "Lectura123")
        self.assertIsNone(error)
        self.assertTrue(sesion.puede("apu.ver"))
        self.assertFalse(sesion.puede("apu.editar"))
        self.assertFalse(sesion.puede("usuarios.gestionar"))

    def test_reglas_de_fortaleza(self):
        self.assertEqual(validar_fortaleza("ClaveSegura1"), [])
        self.assertTrue(validar_fortaleza("debil"))


if __name__ == "__main__":
    unittest.main()
