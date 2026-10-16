"""Control de licencia y prueba gratuita, confinado a la carpeta indicada."""
import json
import shutil
from datetime import datetime, timedelta
from pathlib import Path

from bap_apu.data.db import Database
from bap_apu.data.repos import empresas
from bap_apu.errores import ErrorValidacion
from bap_apu.licensing import offline_license
from bap_apu.licensing.offline_license import EstadoLicencia


class LicenciaService:
    def __init__(self, db: Database, carpeta: Path):
        self.db = db
        self.carpeta = Path(carpeta)

    def _leer_licencia_instalada(self):
        ruta = self.carpeta / "licencia.apulic"
        if not ruta.exists():
            return None
        try:
            return json.loads(ruta.read_text(encoding="utf-8"))
        except Exception:
            return None

    def _inicializar_control_prueba(self, conn):
        fila = conn.execute("SELECT inicio,ultimo_uso,codigo_equipo FROM control_prueba WHERE id=1").fetchone()
        marcador = offline_license.leer_marcador(self.carpeta)
        ahora = datetime.now().replace(microsecond=0)
        if not fila and not marcador:
            inicio = ahora.isoformat()
            conn.execute("INSERT INTO control_prueba(id,inicio,ultimo_uso,codigo_equipo) VALUES (1,?,?,?)",
                         (inicio, inicio, offline_license.codigo_equipo()))
            offline_license.guardar_marcador(self.carpeta, inicio, inicio)
        elif not fila and marcador:
            conn.execute("INSERT INTO control_prueba(id,inicio,ultimo_uso,codigo_equipo) VALUES (1,?,?,?)",
                         (marcador["inicio"], marcador["ultimo_uso"], offline_license.codigo_equipo()))

    def verificar_acceso(self) -> EstadoLicencia:
        licencia = self._leer_licencia_instalada()
        if licencia:
            estado = offline_license.validar_payload(licencia)
            if estado.permitido:
                return estado
        with self.db.transaccion() as conn:
            self._inicializar_control_prueba(conn)
            inicio_db, ultimo_db, _ = conn.execute(
                "SELECT inicio,ultimo_uso,codigo_equipo FROM control_prueba WHERE id=1").fetchone()
            marcador = offline_license.leer_marcador(self.carpeta) or {"inicio": inicio_db, "ultimo_uso": ultimo_db}
            inicio = min(datetime.fromisoformat(inicio_db), datetime.fromisoformat(marcador["inicio"]))
            ultimo = max(datetime.fromisoformat(ultimo_db), datetime.fromisoformat(marcador["ultimo_uso"]))
            ahora = datetime.now().replace(microsecond=0)
            if ahora + timedelta(hours=12) < ultimo:
                return EstadoLicencia(False, "BLOQUEADA", "Se detectó un cambio irregular en la fecha del equipo.", 0)
            limite = inicio + timedelta(days=offline_license.TRIAL_DAYS)
            dias = max(0, (limite.date() - ahora.date()).days)
            conn.execute("UPDATE control_prueba SET ultimo_uso=? WHERE id=1", (ahora.isoformat(),))
            offline_license.guardar_marcador(self.carpeta, inicio.isoformat(), ahora.isoformat())
            if ahora >= limite:
                return EstadoLicencia(False, "PRUEBA_VENCIDA", "La prueba gratuita de 15 días ha finalizado.", 0)
            return EstadoLicencia(True, "PRUEBA", f"Prueba gratuita: {dias} días restantes.", dias, max_usuarios=5)

    def instalar_licencia(self, ruta_archivo) -> EstadoLicencia:
        datos = json.loads(Path(ruta_archivo).read_text(encoding="utf-8"))
        estado = offline_license.validar_payload(datos)
        if not estado.permitido:
            raise ErrorValidacion(estado.mensaje)
        self.carpeta.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ruta_archivo, self.carpeta / "licencia.apulic")
        with self.db.transaccion() as conn:
            empresas.actualizar_por_licencia(conn, estado.ruc, estado.empresa)
        return estado

    def max_usuarios(self) -> int:
        return self.verificar_acceso().max_usuarios
