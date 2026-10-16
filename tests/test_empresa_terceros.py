import pytest

from bap_apu.contexto import Contexto
from bap_apu.errores import ErrorValidacion, PermisoDenegado
from bap_apu.services.empresa import EmpresaService
from bap_apu.services.licencias import LicenciaService
from bap_apu.services.terceros import TercerosService


@pytest.fixture
def empresa(db, tmp_path):
    return EmpresaService(db, LicenciaService(db, tmp_path))


@pytest.fixture
def terceros(db):
    return TercerosService(db)


def _ctx_ingeniero(db, ctx_admin):
    with db.lectura() as conn:
        permisos = frozenset(f[0] for f in conn.execute(
            """SELECT p.codigo FROM rol_permisos rp
               JOIN permisos p ON p.id = rp.permiso_id
               JOIN roles r ON r.id = rp.rol_id WHERE r.nombre = 'Ingeniero'"""))
    return Contexto(usuario_id=98, usuario="ing", nombre_completo="Ingeniero",
                    rol="Ingeniero", permisos=permisos,
                    empresa_id=ctx_admin.empresa_id, token="t")


def test_empresa_clientes_proveedores_dashboard(db, ctx_admin, empresa, terceros):
    terceros.crear_cliente(ctx_admin, "RUC", "20123456789", "Cliente Uno", "Lima", "999", "cliente@test.pe")
    terceros.crear_proveedor(ctx_admin, "20987654321", "Proveedor Uno", "Ana", "988", "proveedor@test.pe")
    with db.transaccion() as conn:
        conn.execute("INSERT INTO proyectos(nombre, empresa_id) VALUES (?, ?)",
                     ("Proyecto Empresa", ctx_admin.empresa_id))
        conn.execute("INSERT INTO recursos(nombre, unidad, precio, tipo, empresa_id) VALUES (?,?,?,?,?)",
                     ("Recurso Empresa", "UND", 25, "Material", ctx_admin.empresa_id))
    assert len(terceros.listar_clientes(ctx_admin)) == 1
    assert len(terceros.listar_proveedores(ctx_admin)) == 1
    datos = empresa.obtener_dashboard(ctx_admin)
    assert datos["proyectos"] == 1
    assert datos["clientes"] == 1
    assert datos["recursos"] == 1


def test_razon_social_obligatoria(ctx_admin, empresa):
    with pytest.raises(ErrorValidacion):
        empresa.guardar_empresa(ctx_admin, "20111111111", "  ", "Comercial", "", "", "")


def test_ingeniero_no_crea_clientes(db, ctx_admin, terceros):
    with pytest.raises(PermisoDenegado):
        terceros.crear_cliente(_ctx_ingeniero(db, ctx_admin), "RUC", "", "Cliente", "", "", "")


def test_alta_cliente_audita(ctx_admin, empresa, terceros):
    terceros.crear_cliente(ctx_admin, "RUC", "", "Cliente Auditado", "", "", "")
    acciones = [fila[2] for fila in empresa.listar_auditoria(ctx_admin)]
    assert "CLIENTE_CREADO" in acciones


def test_estado_licencia_prueba(ctx_admin, empresa):
    assert empresa.estado_licencia(ctx_admin)[0] == "PRUEBA"


def test_configuracion_y_empresa_principal(ctx_admin, empresa):
    empresa.guardar_configuracion(ctx_admin, {"igv": 0.18})
    assert empresa.obtener_configuracion(ctx_admin)["igv"] == "0.18"
    assert empresa.empresa_principal(ctx_admin.usuario_id)[0] == ctx_admin.empresa_id
