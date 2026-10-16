import base64
import json
import unittest
from datetime import date, timedelta
from unittest.mock import patch

from cryptography.hazmat.primitives import serialization

from services import offline_license


PRIVATE_TEST_KEY = b"""-----BEGIN PRIVATE KEY-----
MC4CAQAwBQYDK2VwBCIEID3cCDR00zXTEiK8N/+4RcrIBL3bwrFQWcOdbjXvqdGq
-----END PRIVATE KEY-----
"""


class LicenciaBAPTests(unittest.TestCase):
    def test_rechaza_producto_ajeno(self):
        key = serialization.load_pem_private_key(PRIVATE_TEST_KEY, password=None)
        public = key.public_key().public_bytes(serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)
        payload = {
            "company": "Cliente Prueba", "devices": ["AAAAA-BBBBB-CCCCC-DDDDD-EEEEE"],
            "expires": (date.today() + timedelta(days=30)).isoformat(), "max_users": 2,
            "product": "Otro producto", "ruc": "20123456789",
        }
        canonico = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
        documento = {"payload": payload, "signature": base64.b64encode(key.sign(canonico)).decode()}
        with patch.object(offline_license, "PUBLIC_KEY_DER_B64", base64.b64encode(public).decode()), patch.object(offline_license, "codigo_equipo", return_value=payload["devices"][0]):
            estado = offline_license._validar_payload(documento)
        self.assertFalse(estado.permitido)
        self.assertEqual(estado.modo, "INVALIDA")


if __name__ == "__main__":
    unittest.main()
