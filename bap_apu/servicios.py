"""Contenedor de servicios: se arma una vez al iniciar y lo comparte la interfaz."""
from dataclasses import dataclass
from pathlib import Path

from bap_apu.data.db import Database
from bap_apu.services.apu import ApuService
from bap_apu.services.auth import AuthService
from bap_apu.services.empresa import EmpresaService
from bap_apu.services.importacion import ImportacionService
from bap_apu.services.licencias import LicenciaService
from bap_apu.services.partidas import PartidasService
from bap_apu.services.proyectos import ProyectosService
from bap_apu.services.recursos import RecursosService
from bap_apu.services.reportes import ReportesService
from bap_apu.services.respaldos import RespaldoService
from bap_apu.services.terceros import TercerosService


@dataclass(frozen=True)
class Servicios:
    db: Database
    licencias: LicenciaService
    auth: AuthService
    empresa: EmpresaService
    terceros: TercerosService
    proyectos: ProyectosService
    recursos: RecursosService
    apu: ApuService
    partidas: PartidasService
    importacion: ImportacionService
    respaldos: RespaldoService
    reportes: ReportesService


def crear_servicios(db: Database, carpeta_datos: Path) -> Servicios:
    licencias = LicenciaService(db, carpeta_datos)
    return Servicios(
        db=db,
        licencias=licencias,
        auth=AuthService(db, licencias.max_usuarios),
        empresa=EmpresaService(db, licencias),
        terceros=TercerosService(db),
        proyectos=ProyectosService(db),
        recursos=RecursosService(db),
        apu=ApuService(db),
        partidas=PartidasService(db),
        importacion=ImportacionService(db),
        respaldos=RespaldoService(db, carpeta_datos),
        reportes=ReportesService(db),
    )
