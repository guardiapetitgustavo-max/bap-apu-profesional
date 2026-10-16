from pathlib import Path

from bap_apu import brand

RAIZ = Path(__file__).resolve().parents[1]


def test_identidad():
    assert brand.APP_NAME == "BAP APU Profesional"
    assert brand.APP_VERSION == "1.5.0"
    assert brand.WHATSAPP == "+51 904 170 143"


def test_no_referencias_dyd_en_codigo_de_producto():
    rutas = [RAIZ / "main.py", RAIZ / "bap_apu" / "reports" / "pdf.py", RAIZ / "main.spec"]
    contenido = "\n".join(r.read_text(encoding="utf-8") for r in rutas)
    assert "D&D" not in contenido
    assert "dyd.png" not in contenido


def test_assets():
    for nombre in ("bap_isotipo.png", "bap_logo_principal.png", "bap_apu.ico"):
        assert (RAIZ / "assets" / nombre).is_file()


def test_sin_modulos_legados():
    for nombre in ("database.py", "services", "views", "exportar_pdf.py"):
        assert not (RAIZ / nombre).exists(), nombre
