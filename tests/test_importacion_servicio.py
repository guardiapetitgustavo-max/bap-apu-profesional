from pathlib import Path

import pytest

from bap_apu.contexto import Contexto
from bap_apu.errores import ErrorValidacion, PermisoDenegado
from bap_apu.services.importacion import ImportacionService

CABECERA = ("Codigo_Recurso;Nombre_Recurso;Unidad;Tipo;Marca;Precio;Proveedor_RUC;Proveedor;"
            "Calidad_1_a_5;Stock;Plazo_Entrega_Dias;Fecha_Precio;Actualizar_Precio;URL_Fuente\n")


@pytest.fixture
def csv_precios(tmp_path):
    ruta = tmp_path / "precios.csv"
    ruta.write_text(
        CABECERA
        + "MAT-001;Cemento Tipo I;BOL;Material;Sol;30,90;20111111111;Proveedor Uno;5;100;1;2026-09-12;NO;https://uno.test\n"
        + "MAT-001;Cemento Tipo I;BOL;Material;Sol;29,80;20222222222;Proveedor Dos;4;80;2;2026-09-12;SI;https://dos.test\n",
        encoding="utf-8",
    )
    return ruta


def _contar(db, tabla):
    with db.lectura() as conn:
        return conn.execute(f"SELECT COUNT(*) FROM {tabla}").fetchone()[0]


def test_importa_recurso_dos_ofertas_y_actualiza_precio(db, ctx_admin, csv_precios):
    servicio = ImportacionService(db)
    previa = servicio.previsualizar(ctx_admin, csv_precios)
    assert [f["accion"] for f in previa] == ["CREAR", "OFERTA"]
    resultado = servicio.ejecutar(ctx_admin, csv_precios)
    assert resultado["nuevos"] == 1
    assert resultado["ofertas"] == 2
    with db.lectura() as conn:
        recurso = conn.execute("SELECT id,precio FROM recursos WHERE codigo='MAT-001'").fetchone()
        assert recurso[1] == 29.80
        assert conn.execute("SELECT COUNT(*) FROM proveedor_precios WHERE recurso_id=?", (recurso[0],)).fetchone()[0] == 2
        assert conn.execute("SELECT COUNT(*) FROM historial_precios WHERE recurso_id=?", (recurso[0],)).fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM auditoria WHERE accion='RECURSOS_IMPORTADOS'").fetchone()[0] == 1


def test_rechaza_columnas_incompletas(db, ctx_admin, tmp_path):
    ruta = tmp_path / "malo.csv"
    ruta.write_text("Nombre_Recurso;Precio\nCemento;30\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Faltan columnas"):
        ImportacionService(db).previsualizar(ctx_admin, ruta)


def test_importacion_fallida_no_deja_rastros(db, ctx_admin, csv_precios, monkeypatch):
    from bap_apu.data.repos import precios

    original = precios.insertar_oferta
    llamadas = []

    def falla_a_la_mitad(*args, **kwargs):
        llamadas.append(1)
        if len(llamadas) == 2:
            raise RuntimeError("fallo simulado")
        return original(*args, **kwargs)

    monkeypatch.setattr(precios, "insertar_oferta", falla_a_la_mitad)
    recursos_antes = _contar(db, "recursos")
    importaciones_antes = _contar(db, "importaciones_recursos")
    with pytest.raises(RuntimeError):
        ImportacionService(db).ejecutar(ctx_admin, csv_precios)
    assert len(llamadas) == 2
    assert _contar(db, "recursos") == recursos_antes
    assert _contar(db, "importaciones_recursos") == importaciones_antes
    assert _contar(db, "proveedor_precios") == 0


def test_presupuestador_no_importa(db, ctx_admin, csv_precios):
    with db.lectura() as conn:
        permisos = frozenset(f[0] for f in conn.execute(
            """SELECT p.codigo FROM rol_permisos rp JOIN permisos p ON p.id = rp.permiso_id
               JOIN roles r ON r.id = rp.rol_id WHERE r.nombre = 'Presupuestador'"""))
    ctx = Contexto(usuario_id=ctx_admin.usuario_id, usuario="pres", nombre_completo="Pres",
                   rol="Presupuestador", permisos=permisos, empresa_id=ctx_admin.empresa_id, token="t")
    servicio = ImportacionService(db)
    with pytest.raises(PermisoDenegado):
        servicio.ejecutar(ctx, csv_precios)
    with pytest.raises(PermisoDenegado):
        servicio.previsualizar(ctx, csv_precios)


def test_sin_filas_validas_es_error_de_validacion(db, ctx_admin, tmp_path):
    ruta = tmp_path / "invalido.csv"
    ruta.write_text("Nombre_Recurso;Unidad;Tipo;Precio\nX;UND;Raro;5\n", encoding="utf-8")
    with pytest.raises(ErrorValidacion, match="No existen filas válidas"):
        ImportacionService(db).ejecutar(ctx_admin, ruta)
