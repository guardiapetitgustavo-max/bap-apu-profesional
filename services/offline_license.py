import base64
import hashlib
import hmac
import json
import os
import platform
import shutil
import sys
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from database import conectar, conexion


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


def carpeta_datos():
    if sys.platform == "win32":
        base = os.getenv("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
    else:
        base = os.getenv("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
    ruta = Path(base) / "BAP_APU_Profesional"
    ruta.mkdir(parents=True, exist_ok=True)
    return ruta


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


def inicializar_control_prueba():
    with conexion() as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS control_prueba (
            id INTEGER PRIMARY KEY CHECK(id=1), inicio TEXT NOT NULL,
            ultimo_uso TEXT NOT NULL, codigo_equipo TEXT NOT NULL)""")
        fila = conn.execute("SELECT inicio,ultimo_uso,codigo_equipo FROM control_prueba WHERE id=1").fetchone()
        marcador = _leer_marcador()
        ahora = datetime.now().replace(microsecond=0)
        if not fila and not marcador:
            inicio = ahora.isoformat()
            conn.execute("INSERT INTO control_prueba(id,inicio,ultimo_uso,codigo_equipo) VALUES (1,?,?,?)", (inicio,inicio,codigo_equipo()))
            _guardar_marcador(inicio,inicio)
        elif not fila and marcador:
            conn.execute("INSERT INTO control_prueba(id,inicio,ultimo_uso,codigo_equipo) VALUES (1,?,?,?)", (marcador["inicio"],marcador["ultimo_uso"],codigo_equipo()))


def verificar_acceso():
    licencia = _leer_licencia_instalada()
    if licencia:
        estado = _validar_payload(licencia)
        if estado.permitido:
            return estado
    inicializar_control_prueba()
    with conexion() as conn:
        inicio_db, ultimo_db, _ = conn.execute("SELECT inicio,ultimo_uso,codigo_equipo FROM control_prueba WHERE id=1").fetchone()
        marcador = _leer_marcador() or {"inicio": inicio_db, "ultimo_uso": ultimo_db}
        inicio = min(datetime.fromisoformat(inicio_db), datetime.fromisoformat(marcador["inicio"]))
        ultimo = max(datetime.fromisoformat(ultimo_db), datetime.fromisoformat(marcador["ultimo_uso"]))
        ahora = datetime.now().replace(microsecond=0)
        if ahora + timedelta(hours=12) < ultimo:
            return EstadoLicencia(False,"BLOQUEADA","Se detectó un cambio irregular en la fecha del equipo.",0)
        limite = inicio + timedelta(days=TRIAL_DAYS)
        dias = max(0, (limite.date() - ahora.date()).days)
        conn.execute("UPDATE control_prueba SET ultimo_uso=? WHERE id=1", (ahora.isoformat(),))
        _guardar_marcador(inicio.isoformat(), ahora.isoformat())
        if ahora >= limite:
            return EstadoLicencia(False,"PRUEBA_VENCIDA","La prueba gratuita de 15 días ha finalizado.",0)
        return EstadoLicencia(True,"PRUEBA",f"Prueba gratuita: {dias} días restantes.",dias,max_usuarios=5)


def instalar_licencia(ruta_archivo):
    datos = json.loads(Path(ruta_archivo).read_text(encoding="utf-8"))
    estado = _validar_payload(datos)
    if not estado.permitido:
        raise ValueError(estado.mensaje)
    destino = carpeta_datos() / "licencia.apulic"
    shutil.copy2(ruta_archivo, destino)
    with conexion() as conn:
        empresa = conn.execute("SELECT id FROM empresas ORDER BY id LIMIT 1").fetchone()
        if empresa:
            conn.execute("UPDATE empresas SET ruc=?,razon_social=?,nombre_comercial=? WHERE id=?", (estado.ruc,estado.empresa,estado.empresa,empresa[0]))
    return estado


def _validar_payload(documento):
    try:
        payload = documento["payload"]
        firma = base64.b64decode(documento["signature"])
        canonico = json.dumps(payload,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode("utf-8")
        public = serialization.load_der_public_key(base64.b64decode(PUBLIC_KEY_DER_B64))
        public.verify(firma,canonico)
        if payload.get("product") != "BAP APU Profesional":
            raise ValueError("La licencia no corresponde a BAP APU Profesional.")
        dispositivos = list(dict.fromkeys(payload["devices"]))
        if not 1 <= len(dispositivos) <= MAX_DEVICES:
            raise ValueError("La licencia debe contener entre 1 y 5 equipos.")
        if codigo_equipo() not in dispositivos:
            return EstadoLicencia(False,"EQUIPO_NO_AUTORIZADO","Este equipo no está incluido en la licencia.",0)
        vence = date.fromisoformat(payload["expires"])
        if vence < date.today():
            return EstadoLicencia(False,"VENCIDA",f"La licencia venció el {vence.isoformat()}.",0)
        if not str(payload["ruc"]).isdigit() or len(str(payload["ruc"])) != 11:
            raise ValueError("RUC inválido en la licencia.")
        dias = (vence-date.today()).days
        max_usuarios = int(payload.get("max_users", 5))
        if not 1 <= max_usuarios <= 5:
            raise ValueError("Cantidad de usuarios inválida.")
        return EstadoLicencia(True,"LICENCIA",f"Licencia activa hasta {vence.isoformat()}.",dias,str(payload["ruc"]),payload["company"],vence.isoformat(),max_usuarios)
    except Exception as exc:
        return EstadoLicencia(False,"INVALIDA",f"Licencia inválida: {exc}",0)


def _leer_licencia_instalada():
    ruta = carpeta_datos() / "licencia.apulic"
    if not ruta.exists(): return None
    try:return json.loads(ruta.read_text(encoding="utf-8"))
    except Exception:return None


def _marcador_path(): return carpeta_datos() / ".trial.dat"
def _firma_marcador(payload): return hmac.new(MARKER_SECRET,payload.encode(),hashlib.sha256).hexdigest()
def _guardar_marcador(inicio,ultimo):
    payload=json.dumps({"inicio":inicio,"ultimo_uso":ultimo},sort_keys=True,separators=(",",":"))
    _marcador_path().write_text(json.dumps({"payload":payload,"mac":_firma_marcador(payload)}),encoding="utf-8")
def _leer_marcador():
    try:
        doc=json.loads(_marcador_path().read_text(encoding="utf-8"));payload=doc["payload"]
        if not hmac.compare_digest(doc["mac"],_firma_marcador(payload)):return None
        return json.loads(payload)
    except Exception:return None
