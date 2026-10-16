"""Exportación de reportes Excel y PDF."""
from pathlib import Path

from bap_apu.contexto import Contexto
from bap_apu.core.calculo import agrupar_subtotales
from bap_apu.data.db import Database
from bap_apu.data.repos import apu, reportes
from bap_apu.errores import ErrorValidacion
from bap_apu.reports.excel import HojaReporte, escribir_libro
from bap_apu.reports.pdf import exportar_apu_pdf
from bap_apu.services.proyectos import exigir_proyecto_propio


class ReportesService:
    def __init__(self, db: Database):
        self._db = db

    def exportar_excel(self, ctx: Contexto, ruta) -> Path:
        ctx.exigir("reportes.exportar")
        with self._db.lectura() as conn:
            e = ctx.empresa_id
            hojas = [
                HojaReporte("Resumen", "RESUMEN DE PROYECTOS",
                            ["ID", "Proyecto", "Estado", "Cliente", "Costo APU (S/)"],
                            reportes.proyectos_resumen(conn, e)),
                HojaReporte("Recursos", "CATÁLOGO DE RECURSOS",
                            ["Nombre", "Unidad", "Precio (S/)", "Tipo"],
                            reportes.recursos(conn, e)),
                HojaReporte("Partidas", "BIBLIOTECA DE PARTIDAS",
                            ["Partida", "Unidad", "Costo referencial (S/)"],
                            reportes.partidas(conn)),
                HojaReporte("Precios Proveedores", "PRECIOS DE PROVEEDORES",
                            ["Recurso", "Proveedor", "Marca", "Precio (S/)", "Calidad", "Stock",
                             "Entrega (días)", "Fecha", "Fuente"],
                            reportes.precios_proveedores(conn, e)),
                HojaReporte("Historial Precios", "HISTORIAL DE PRECIOS",
                            ["Fecha", "Recurso", "Precio anterior", "Precio nuevo", "Origen", "Proveedor"],
                            reportes.historial_precios(conn, e)),
            ]
        return escribir_libro(ruta, hojas)

    def exportar_apu_pdf(self, ctx: Contexto, proyecto_id, nombre_proyecto, ruta) -> Path:
        ctx.exigir("apu.exportar")
        with self._db.lectura() as conn:
            exigir_proyecto_propio(conn, proyecto_id, ctx.empresa_id)
            datos = apu.detalle(conn, proyecto_id)
            if not datos:
                raise ErrorValidacion("Este proyecto no tiene recursos asignados en el APU.")
            subtotales = agrupar_subtotales(apu.tipos_y_parciales(conn, proyecto_id))
            total = apu.total(conn, proyecto_id)
        exportar_apu_pdf(nombre_proyecto, datos, subtotales, total, str(ruta))
        return Path(ruta)
