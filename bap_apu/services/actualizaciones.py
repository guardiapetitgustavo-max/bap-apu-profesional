import json
from urllib.request import urlopen
from bap_apu.brand import APP_VERSION, UPDATE_MANIFEST_URL


def consultar_actualizacion(url=None):
    url = url or UPDATE_MANIFEST_URL
    if not url:
        return {"configurado": False, "version_actual": APP_VERSION, "mensaje": "Servidor de actualizaciones pendiente de configurar."}
    with urlopen(url, timeout=8) as respuesta:
        datos = json.loads(respuesta.read().decode("utf-8"))
    nueva = str(datos.get("version", ""))
    return {
        "configurado": True,
        "version_actual": APP_VERSION,
        "version_disponible": nueva,
        "hay_actualizacion": _version(nueva) > _version(APP_VERSION),
        "url": datos.get("url"),
        "notas": datos.get("notas", ""),
    }


def _version(valor):
    try:return tuple(int(x) for x in valor.split("."))
    except Exception:return (0,)
