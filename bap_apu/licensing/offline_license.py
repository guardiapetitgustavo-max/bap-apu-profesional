"""Validación de licencias firmadas y marcador de prueba (sin SQL)."""
import base64
import hashlib
import hmac
import json
import platform
import sys
import uuid
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from cryptography.hazmat.primitives import serialization

PUBLIC_KEY_DER_B64 = "MCowBQYDK2VwAyEAW4ztBQMWmPl7KlLS9nicavQ4joZghmFe8Gb1SQZGkS4="
TRIAL_DAYS = 15
MAX_DEVICES = 5
MARKER_SECRET = b"BAP-APU-OFFLINE-TRIAL-V1-2026"


@dataclass(frozen=True)
class EstadoLicencia:
    permitido: bool
    modo: str
    mensaje: str
    dias_restantes: int
    ruc: str = ""
    empresa: str = ""
    vencimiento: str = ""
    max_usuarios: int = 5


def codigo_equipo():
    partes = [platform.system(), platform.machine(), str(uuid.getnode())]
    if sys.platform == "win32":
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Cryptography") as key:
                partes.append(str(winreg.QueryValueEx(key, "MachineGuid")[0]))
        except OSError:
            pass
    digest = hashlib.sha256("|".join(partes).encode("utf-8")).hexdigest().upper()
    return "-".join(digest[i:i+5] for i in range(0, 25, 5))


def validar_payload(documento):
    try:
        payload = documento["payload"]
        firma = base64.b64decode(documento["signature"])
        canonico = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        public = serialization.load_der_public_key(base64.b64decode(PUBLIC_KEY_DER_B64))
        public.verify(firma, canonico)
        if payload.get("product") != "BAP APU Profesional":
            raise ValueError("La licencia no corresponde a BAP APU Profesional.")
        dispositivos = list(dict.fromkeys(payload["devices"]))
        if not 1 <= len(dispositivos) <= MAX_DEVICES:
            raise ValueError("La licencia debe contener entre 1 y 5 equipos.")
        if codigo_equipo() not in dispositivos:
            return EstadoLicencia(False, "EQUIPO_NO_AUTORIZADO", "Este equipo no está incluido en la licencia.", 0)
        vence = date.fromisoformat(payload["expires"])
        if vence < date.today():
            return EstadoLicencia(False, "VENCIDA", f"La licencia venció el {vence.isoformat()}.", 0)
        if not str(payload["ruc"]).isdigit() or len(str(payload["ruc"])) != 11:
            raise ValueError("RUC inválido en la licencia.")
        dias = (vence - date.today()).days
        max_usuarios = int(payload.get("max_users", 5))
        if not 1 <= max_usuarios <= 5:
            raise ValueError("Cantidad de usuarios inválida.")
        return EstadoLicencia(True, "LICENCIA", f"Licencia activa hasta {vence.isoformat()}.", dias,
                              str(payload["ruc"]), payload["company"], vence.isoformat(), max_usuarios)
    except Exception as exc:
        return EstadoLicencia(False, "INVALIDA", f"Licencia inválida: {exc}", 0)


def _marcador_path(carpeta):
    return Path(carpeta) / ".trial.dat"


def _firma_marcador(payload):
    return hmac.new(MARKER_SECRET, payload.encode(), hashlib.sha256).hexdigest()


def guardar_marcador(carpeta, inicio, ultimo):
    payload = json.dumps({"inicio": inicio, "ultimo_uso": ultimo}, sort_keys=True, separators=(",", ":"))
    _marcador_path(carpeta).write_text(
        json.dumps({"payload": payload, "mac": _firma_marcador(payload)}), encoding="utf-8")


def leer_marcador(carpeta):
    try:
        doc = json.loads(_marcador_path(carpeta).read_text(encoding="utf-8"))
        payload = doc["payload"]
        if not hmac.compare_digest(doc["mac"], _firma_marcador(payload)):
            return None
        return json.loads(payload)
    except Exception:
        return None
