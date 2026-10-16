import base64
import json
import os
from datetime import date, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest
from cryptography.hazmat.primitives import serialization

from bap_apu.licensing import offline_license
from bap_apu.services.licencias import LicenciaService

PRIVATE_TEST_KEY = b"""-----BEGIN PRIVATE KEY-----
MC4CAQAwBQYDK2VwBCIEID3cCDR00zXTEiK8N/+4RcrIBL3bwrFQWcOdbjXvqdGq
-----END PRIVATE KEY-----
"""
EQUIPO = "AAAAA-BBBBB-CCCCC-DDDDD-EEEEE"


def _firmar(producto, max_users=2):
    key = serialization.load_pem_private_key(PRIVATE_TEST_KEY, password=None)
    public = key.public_key().public_bytes(
        serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)
    payload = {
        "company": "Cliente Prueba", "devices": [EQUIPO],
        "expires": (date.today() + timedelta(days=30)).isoformat(), "max_users": max_users,
        "product": producto, "ruc": "20123456789",
    }
    canonico = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    documento = {"payload": payload, "signature": base64.b64encode(key.sign(canonico)).decode()}
    return documento, base64.b64encode(public).decode()


def _validar(documento, public_b64):
    with patch.object(offline_license, "PUBLIC_KEY_DER_B64", public_b64), \
            patch.object(offline_license, "codigo_equipo", return_value=EQUIPO):
        return offline_license.validar_payload(documento)


@pytest.fixture
def servicio(db, tmp_path):
    carpeta = tmp_path / "datos_licencia"
    carpeta.mkdir()
    return LicenciaService(db, carpeta)


def test_clave_publica_intacta():
    assert offline_license.PUBLIC_KEY_DER_B64 == "MCowBQYDK2VwAyEAW4ztBQMWmPl7KlLS9nicavQ4joZghmFe8Gb1SQZGkS4="


def test_rechaza_producto_ajeno():
    estado = _validar(*_firmar("Otro producto"))
    assert not estado.permitido
    assert estado.modo == "INVALIDA"


def test_licencia_valida_formato_1_4_0():
    estado = _validar(*_firmar("BAP APU Profesional", max_users=3))
    assert estado.permitido
    assert estado.modo == "LICENCIA"
    assert estado.max_usuarios == 3


def test_prueba_nueva_15_dias(servicio):
    estado = servicio.verificar_acceso()
    assert estado.modo == "PRUEBA"
    assert estado.dias_restantes in (14, 15)
    assert servicio.max_usuarios() == 5


def test_detecta_fecha_atrasada(servicio, db):
    servicio.verificar_acceso()
    futuro = (datetime.now() + timedelta(days=2)).replace(microsecond=0).isoformat()
    with db.transaccion() as conn:
        conn.execute("UPDATE control_prueba SET ultimo_uso=? WHERE id=1", (futuro,))
    inicio = (datetime.now() - timedelta(days=1)).replace(microsecond=0).isoformat()
    offline_license.guardar_marcador(servicio.carpeta, inicio, futuro)
    estado = servicio.verificar_acceso()
    assert estado.modo == "BLOQUEADA"
    assert not estado.permitido


def test_escribe_solo_en_su_carpeta(servicio):
    # Las pruebas del código legado pueden haber creado ya un marcador en el
    # LOCALAPPDATA aislado; lo que importa es que el servicio no lo toque.
    ajeno = Path(os.environ["LOCALAPPDATA"]) / "BAP_APU_Profesional" / ".trial.dat"
    antes = ajeno.read_bytes() if ajeno.exists() else None
    servicio.verificar_acceso()
    assert (servicio.carpeta / ".trial.dat").exists()
    despues = ajeno.read_bytes() if ajeno.exists() else None
    assert despues == antes


def test_marcador_alterado_se_ignora(tmp_path):
    offline_license.guardar_marcador(tmp_path, "2026-01-01T00:00:00", "2026-01-02T00:00:00")
    assert offline_license.leer_marcador(tmp_path)["inicio"] == "2026-01-01T00:00:00"
    ruta = tmp_path / ".trial.dat"
    ruta.write_text(ruta.read_text(encoding="utf-8").replace("2026-01-01", "2020-01-01"), encoding="utf-8")
    assert offline_license.leer_marcador(tmp_path) is None


def test_instalar_licencia_copia_y_actualiza_empresa(servicio, db, tmp_path):
    documento, public_b64 = _firmar("BAP APU Profesional")
    origen = tmp_path / "cliente.apulic"
    origen.write_text(json.dumps(documento), encoding="utf-8")
    with patch.object(offline_license, "PUBLIC_KEY_DER_B64", public_b64), \
            patch.object(offline_license, "codigo_equipo", return_value=EQUIPO):
        estado = servicio.instalar_licencia(origen)
        assert estado.modo == "LICENCIA"
        assert (servicio.carpeta / "licencia.apulic").exists()
        assert servicio.verificar_acceso().max_usuarios == 2
    with db.lectura() as conn:
        ruc, razon = conn.execute("SELECT ruc, razon_social FROM empresas ORDER BY id LIMIT 1").fetchone()
    assert (ruc, razon) == ("20123456789", "Cliente Prueba")
