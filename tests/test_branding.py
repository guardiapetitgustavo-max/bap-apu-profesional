import unittest
from pathlib import Path

import brand


class BrandingTests(unittest.TestCase):
    def test_identidad(self):
        self.assertEqual(brand.APP_NAME, "BAP APU Profesional")
        self.assertEqual(brand.APP_VERSION, "1.4.0")
        self.assertEqual(brand.WHATSAPP, "+51 904 170 143")

    def test_no_referencias_dyd_en_codigo_de_producto(self):
        raiz = Path(__file__).resolve().parents[1]
        rutas = [raiz / "main.py", raiz / "exportar_pdf.py", raiz / "main.spec"]
        contenido = "\n".join(r.read_text(encoding="utf-8") for r in rutas)
        self.assertNotIn("D&D", contenido)
        self.assertNotIn("dyd.png", contenido)

    def test_assets(self):
        raiz = Path(__file__).resolve().parents[1]
        for nombre in ("bap_isotipo.png", "bap_logo_principal.png", "bap_apu.ico"):
            self.assertTrue((raiz / "assets" / nombre).is_file())


if __name__ == "__main__":
    unittest.main()
