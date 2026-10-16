"""Importación de recursos y ofertas de proveedores desde .xlsx / .csv."""
from pathlib import Path

from bap_apu.contexto import Contexto
from bap_apu.data.db import Database
from bap_apu.data.repos import auditoria, importaciones, precios, recursos, terceros
from bap_apu.errores import ErrorValidacion
from bap_apu.services.importacion_archivo import (
    TIPOS, fecha, leer_archivo, normalizar_texto, numero,
)


def _leer(ruta):
    try:
        return leer_archivo(ruta)
    except ErrorValidacion:
        raise
    except ValueError as exc:
        raise ErrorValidacion(str(exc)) from exc


def _calcular_filas(conn, empresa_id, ruta) -> list[dict]:
    existentes = recursos.existentes_para_importar(conn, empresa_id)
    por_codigo = {str(r[1]).strip().upper(): r for r in existentes if r[1]}
    por_nombre = {(normalizar_texto(r[2]), normalizar_texto(r[3])): r for r in existentes}
    nuevas_claves = set()
    filas = []
    for num, bruto in _leer(ruta):
        errores = []
        try:
            nombre = str(bruto.get("Nombre_Recurso") or "").strip()
            unidad = str(bruto.get("Unidad") or "").strip().upper()
            codigo = str(bruto.get("Codigo_Recurso") or "").strip().upper()
            tipo_raw = normalizar_texto(bruto.get("Tipo"))
            tipo = TIPOS.get(tipo_raw)
            precio = numero(bruto.get("Precio"), requerido=True)
            if not nombre: errores.append("nombre obligatorio")
            if not unidad: errores.append("unidad obligatoria")
            if not tipo: errores.append("tipo no reconocido")
            if precio is not None and precio <= 0: errores.append("precio debe ser mayor a cero")
            ruc = str(bruto.get("Proveedor_RUC") or "").strip()
            proveedor = str(bruto.get("Proveedor") or "").strip()
            if ruc and (not ruc.isdigit() or len(ruc) != 11): errores.append("RUC de proveedor inválido")
            calidad_num = numero(bruto.get("Calidad_1_a_5"))
            calidad = int(calidad_num) if calidad_num is not None else None
            if calidad is not None and (calidad_num != calidad or not 1 <= calidad <= 5): errores.append("calidad debe ser un entero entre 1 y 5")
            stock = numero(bruto.get("Stock"))
            plazo_num = numero(bruto.get("Plazo_Entrega_Dias"))
            plazo = int(plazo_num) if plazo_num is not None else None
            if plazo is not None and plazo_num != plazo: errores.append("plazo debe ser un número entero")
            fecha_precio = fecha(bruto.get("Fecha_Precio"))
            actualizar = normalizar_texto(bruto.get("Actualizar_Precio")) in {"si", "s", "yes", "1", "true"}
            recurso = por_codigo.get(codigo) if codigo else None
            recurso = recurso or por_nombre.get((normalizar_texto(nombre), normalizar_texto(unidad)))
            clave_nueva = (codigo or "", normalizar_texto(nombre), normalizar_texto(unidad))
            if recurso and actualizar:
                accion = "ACTUALIZAR"
            elif recurso and (proveedor or ruc):
                accion = "OFERTA"
            elif recurso:
                accion = "SIN CAMBIO"
            elif clave_nueva in nuevas_claves:
                accion = "OFERTA"
            else:
                accion = "CREAR"
                nuevas_claves.add(clave_nueva)
            filas.append({
                "fila": num, "valido": not errores, "errores": "; ".join(errores), "accion": accion,
                "recurso_id": recurso[0] if recurso else None, "codigo": codigo, "nombre": nombre,
                "unidad": unidad, "tipo": tipo, "marca": str(bruto.get("Marca") or "").strip(),
                "precio": precio, "proveedor_ruc": ruc, "proveedor": proveedor,
                "calidad": calidad, "stock": stock, "plazo": plazo, "fecha": fecha_precio,
                "actualizar": actualizar, "fuente": str(bruto.get("URL_Fuente") or "").strip(),
            })
        except (ValueError, TypeError) as exc:
            filas.append({"fila": num, "valido": False, "errores": str(exc), "accion": "ERROR"})
    return filas


class ImportacionService:
    def __init__(self, db: Database):
        self._db = db

    def previsualizar(self, ctx: Contexto, ruta) -> list[dict]:
        ctx.exigir("recursos.editar")
        with self._db.lectura() as conn:
            return _calcular_filas(conn, ctx.empresa_id, ruta)

    def ejecutar(self, ctx: Contexto, ruta) -> dict:
        ctx.exigir("recursos.editar")
        empresa_id = ctx.empresa_id
        nuevos = actualizados = ofertas = 0
        with self._db.transaccion() as conn:
            filas = _calcular_filas(conn, empresa_id, ruta)
            validas = [f for f in filas if f["valido"]]
            if not validas:
                raise ErrorValidacion("No existen filas válidas para importar.")
            existentes = recursos.existentes_para_importar(conn, empresa_id)
            por_codigo = {str(r[1]).strip().upper(): r[0] for r in existentes if r[1]}
            por_nombre = {(normalizar_texto(r[2]), normalizar_texto(r[3])): r[0] for r in existentes}
            for fila in validas:
                clave = (normalizar_texto(fila["nombre"]), normalizar_texto(fila["unidad"]))
                recurso_id = por_codigo.get(fila["codigo"]) if fila["codigo"] else None
                recurso_id = recurso_id or por_nombre.get(clave)
                if recurso_id is None:
                    recurso_id = recursos.insertar(
                        conn, fila["nombre"], fila["unidad"], fila["precio"], fila["tipo"], empresa_id,
                        fila["codigo"] or None, fila["marca"] or None)
                    if fila["codigo"]:
                        por_codigo[fila["codigo"]] = recurso_id
                    por_nombre[clave] = recurso_id
                    nuevos += 1
                else:
                    recursos.actualizar_datos(conn, recurso_id, empresa_id, fila["codigo"],
                                              fila["marca"], fila["tipo"])
                    if fila["actualizar"]:
                        anterior = recursos.precio(conn, recurso_id)
                        recursos.actualizar_precio(conn, recurso_id, fila["precio"])
                        precios.registrar_historial(conn, empresa_id, recurso_id, None,
                                                    anterior, fila["precio"], "IMPORTACION")
                        actualizados += 1
                if fila["proveedor"] or fila["proveedor_ruc"]:
                    if fila["proveedor_ruc"]:
                        encontrado = terceros.buscar_proveedor_por_ruc(conn, empresa_id, fila["proveedor_ruc"])
                    else:
                        encontrado = terceros.buscar_proveedor_por_nombre(conn, empresa_id, fila["proveedor"])
                    if encontrado:
                        proveedor_id = encontrado[0]
                    else:
                        proveedor_id = terceros.insertar_proveedor_minimo(
                            conn, empresa_id, fila["proveedor_ruc"] or None,
                            fila["proveedor"] or f"Proveedor {fila['proveedor_ruc']}")
                    precios.insertar_oferta(
                        conn, empresa_id, proveedor_id, recurso_id, fila["codigo"] or None, fila["nombre"],
                        fila["unidad"], fila["marca"] or None, fila["precio"], fila["calidad"],
                        fila["stock"], fila["plazo"], fila["fuente"] or None, fila["fecha"])
                    ofertas += 1
            omitidos = len(filas) - len(validas)
            ruta = Path(ruta)
            importaciones.registrar(conn, empresa_id, ctx.usuario_id, ruta.name,
                                    ruta.suffix.lower().lstrip("."), len(filas), nuevos,
                                    actualizados, ofertas, omitidos)
            if ctx.usuario_id:
                auditoria.registrar(conn, ctx.usuario_id, "RECURSOS_IMPORTADOS", "recursos",
                                    f"{ruta.name}: {len(validas)} filas")
        return {"filas": len(filas), "validas": len(validas), "nuevos": nuevos,
                "actualizados": actualizados, "ofertas": ofertas, "omitidos": omitidos}
