import time
import tkinter

import pytest

ctk = pytest.importorskip("customtkinter")

from bap_apu.servicios import crear_servicios
from bap_apu.ui.app import AppAPU
from bap_apu.ui.views.activacion import VentanaActivacion
from bap_apu.ui.views.apu import VistaAPU
from bap_apu.ui.views.configuracion import VistaConfiguracion
from bap_apu.ui.views.dashboard import VistaDashboard
from bap_apu.ui.views.partidas import VistaPartidas
from bap_apu.ui.views.proyectos import VistaProyectos
from bap_apu.ui.views.recursos import VistaRecursos
from bap_apu.ui.views.reportes import VistaReportes
from bap_apu.ui.views.terceros import VistaTerceros
from bap_apu.ui.views.usuarios import VistaUsuarios

def _intentar(fabrica):
    """Tk a veces falla al iniciar al crear varias raíces seguidas; se reintenta."""
    ultimo = None
    for _ in range(4):
        try:
            return fabrica()
        except tkinter.TclError as exc:
            ultimo = exc
            time.sleep(0.3)
    pytest.skip(f"Tk no está disponible: {ultimo}")


VISTAS = [VistaDashboard, VistaProyectos, VistaRecursos, VistaAPU, VistaPartidas,
          VistaTerceros, VistaReportes, VistaUsuarios, VistaConfiguracion]


# Las ventanas raíz (activación y app) van primero: una segunda raíz de Tk
# no puede convivir con la raíz compartida de las vistas.

def test_activacion_se_construye(db, tmp_path):
    servicios = crear_servicios(db, tmp_path)
    estado = servicios.licencias.verificar_acceso()
    ventana = _intentar(lambda: VentanaActivacion(servicios, estado))
    ventana.root.withdraw()
    ventana.root.update()
    ventana.root.destroy()


def test_app_se_construye(db, tmp_path, ctx_admin):
    servicios = crear_servicios(db, tmp_path)
    estado = servicios.licencias.verificar_acceso()
    sesion, error = servicios.auth.autenticar("admin", "admin123")
    assert sesion, error
    app = _intentar(lambda: AppAPU(servicios, sesion, ctx_admin, estado))
    app.withdraw()
    app.update()
    app.destroy()


@pytest.fixture(scope="module")
def raiz():
    ventana = _intentar(ctk.CTk)
    ventana.withdraw()
    yield ventana
    ventana.destroy()


@pytest.mark.parametrize("clase", VISTAS)
def test_vista_se_construye(raiz, db, tmp_path, ctx_admin, clase):
    servicios = crear_servicios(db, tmp_path)
    vista = clase(raiz, servicios, ctx_admin)
    vista.update()
    vista.destroy()
