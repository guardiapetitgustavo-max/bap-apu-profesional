import shutil
import sys
from pathlib import Path
import customtkinter as ctk
from tkinter import filedialog, messagebox

from brand import COLOR_GOLD, COLOR_NAVY, COLOR_TEAL
from database import aplicar_precio_oferta, insertar_recurso, obtener_ofertas_recurso, obtener_recursos
from services.importacion_service import ejecutar_importacion, previsualizar_importacion


def resolver_recurso(ruta_relativa):
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1]))
    return base / ruta_relativa


class VistaRecursos(ctk.CTkFrame):
    def __init__(self, parent, can_edit=True, empresa_id=None, usuario_id=None):
        super().__init__(parent)
        self.can_edit, self.empresa_id, self.usuario_id = can_edit, empresa_id, usuario_id
        self.ruta_importacion, self.recursos, self.recursos_dict = None, [], {}
        ctk.CTkLabel(self, text="RECURSOS Y PRECIOS DE PROVEEDORES", font=("Arial", 22, "bold")).pack(pady=(14, 5))
        ctk.CTkLabel(self, text="Catálogo, actualización masiva e historial de ofertas", text_color="#aab7c4", font=("Arial", 11)).pack(pady=(0, 6))
        self.tabs = ctk.CTkTabview(self); self.tabs.pack(fill="both", expand=True, padx=18, pady=(0, 18))
        self._crear_catalogo(self.tabs.add("Catálogo"))
        self._crear_importacion(self.tabs.add("Importar Excel / CSV"))
        self._crear_comparador(self.tabs.add("Comparar proveedores"))
        self.cargar()

    def _crear_catalogo(self, tab):
        contenedor = ctk.CTkFrame(tab, fg_color="transparent"); contenedor.pack(fill="both", expand=True, padx=5, pady=5)
        contenedor.columnconfigure(0, weight=1); contenedor.columnconfigure(1, weight=3); contenedor.rowconfigure(0, weight=1)
        form = ctk.CTkFrame(contenedor, width=270); form.grid(row=0, column=0, sticky="nsw", padx=(0, 12))
        ctk.CTkLabel(form, text="Nuevo recurso", font=("Arial", 15, "bold")).pack(pady=12)
        self.nombre = ctk.CTkEntry(form, placeholder_text="Nombre del recurso", width=230); self.nombre.pack(pady=7)
        self.unidad = ctk.CTkEntry(form, placeholder_text="Unidad (KG, M2, UND)", width=230); self.unidad.pack(pady=7)
        self.precio = ctk.CTkEntry(form, placeholder_text="Precio unitario (S/)", width=230); self.precio.pack(pady=7)
        self.tipo = ctk.CTkOptionMenu(form, values=["Material", "Mano de Obra", "Equipo"], width=230); self.tipo.pack(pady=9)
        self.btn_guardar = ctk.CTkButton(form, text="Guardar recurso", command=self.guardar, fg_color=COLOR_TEAL, width=230); self.btn_guardar.pack(pady=15)
        if not self.can_edit: self.btn_guardar.configure(state="disabled", text="Solo lectura")
        tabla = ctk.CTkFrame(contenedor); tabla.grid(row=0, column=1, sticky="nsew")
        cabecera = ctk.CTkFrame(tabla, fg_color=COLOR_NAVY, height=38); cabecera.pack(fill="x"); cabecera.pack_propagate(False)
        self._celdas(cabecera, (("ID", .08), ("Nombre", .43), ("Unidad", .13), ("Precio", .16), ("Tipo", .20)), True)
        self.scroll_rows = ctk.CTkScrollableFrame(tabla, fg_color="transparent"); self.scroll_rows.pack(fill="both", expand=True, padx=2, pady=2)

    def _crear_importacion(self, tab):
        acciones = ctk.CTkFrame(tab); acciones.pack(fill="x", padx=15, pady=12)
        ctk.CTkButton(acciones, text="Descargar plantilla Excel", command=self.descargar_plantilla, fg_color=COLOR_NAVY).pack(side="left", padx=6, pady=8)
        self.btn_archivo = ctk.CTkButton(acciones, text="Seleccionar Excel o CSV", command=self.seleccionar_archivo, fg_color=COLOR_TEAL); self.btn_archivo.pack(side="left", padx=6)
        self.btn_importar = ctk.CTkButton(acciones, text="Confirmar importación", command=self.importar, fg_color="#2e7d32", state="disabled"); self.btn_importar.pack(side="right", padx=6)
        if not self.can_edit: self.btn_archivo.configure(state="disabled")
        self.lbl_archivo = ctk.CTkLabel(tab, text="Ningún archivo seleccionado", text_color="#aab7c4"); self.lbl_archivo.pack(anchor="w", padx=22)
        self.lbl_resumen = ctk.CTkLabel(tab, text="La vista previa mostrará qué filas se crearán o actualizarán.", text_color=COLOR_GOLD); self.lbl_resumen.pack(anchor="w", padx=22, pady=(4, 8))
        cabecera = ctk.CTkFrame(tab, fg_color=COLOR_NAVY, height=38); cabecera.pack(fill="x", padx=15); cabecera.pack_propagate(False)
        self._celdas(cabecera, (("Fila", .08), ("Acción", .14), ("Recurso", .34), ("Proveedor", .22), ("Precio", .12), ("Estado", .10)), True)
        self.preview_rows = ctk.CTkScrollableFrame(tab, fg_color="transparent"); self.preview_rows.pack(fill="both", expand=True, padx=15, pady=(2, 12))

    def _crear_comparador(self, tab):
        selector = ctk.CTkFrame(tab); selector.pack(fill="x", padx=15, pady=12)
        ctk.CTkLabel(selector, text="Recurso:", font=("Arial", 12, "bold")).pack(side="left", padx=8)
        self.recurso_var = ctk.StringVar(value="Seleccione un recurso")
        self.combo_recurso = ctk.CTkOptionMenu(selector, variable=self.recurso_var, values=["Seleccione un recurso"], width=430, command=lambda _v: self.cargar_ofertas()); self.combo_recurso.pack(side="left", padx=8)
        self.lbl_precio_actual = ctk.CTkLabel(selector, text="Precio actual: -", text_color=COLOR_GOLD, font=("Arial", 12, "bold")); self.lbl_precio_actual.pack(side="right", padx=12)
        cabecera = ctk.CTkFrame(tab, fg_color=COLOR_NAVY, height=38); cabecera.pack(fill="x", padx=15); cabecera.pack_propagate(False)
        self._celdas(cabecera, (("Proveedor", .25), ("Marca", .14), ("Precio", .12), ("Calidad", .10), ("Stock", .10), ("Entrega", .11), ("Fecha", .10), ("Elegir", .08)), True)
        self.ofertas_rows = ctk.CTkScrollableFrame(tab, fg_color="transparent"); self.ofertas_rows.pack(fill="both", expand=True, padx=15, pady=(2, 12))

    @staticmethod
    def _celdas(parent, celdas, bold=False):
        posicion = 0
        for texto, ancho in celdas:
            ctk.CTkLabel(parent, text=texto, anchor="w", font=("Arial", 11, "bold" if bold else "normal"), text_color="white" if bold else None).place(relx=posicion + .01, rely=.15, relwidth=ancho)
            posicion += ancho

    def guardar(self):
        nombre, unidad = self.nombre.get().strip(), self.unidad.get().strip().upper()
        if not nombre or not unidad: messagebox.showwarning("Campos vacíos", "Complete el nombre y la unidad."); return
        try:
            precio = float(self.precio.get().replace(",", "."))
            if precio <= 0: raise ValueError
        except ValueError: messagebox.showerror("Precio inválido", "Ingrese un precio mayor a cero."); return
        insertar_recurso(nombre, unidad, precio, self.tipo.get(), self.empresa_id)
        for entrada in (self.nombre, self.unidad, self.precio): entrada.delete(0, "end")
        self.cargar(); messagebox.showinfo("Recurso", "Recurso registrado correctamente.")

    def cargar(self):
        for widget in self.scroll_rows.winfo_children(): widget.destroy()
        self.recursos = obtener_recursos(self.empresa_id)
        self.recursos_dict = {f"{r[1]} ({r[2]})": r for r in self.recursos}
        self.combo_recurso.configure(values=list(self.recursos_dict) or ["Seleccione un recurso"])
        for index, r in enumerate(self.recursos):
            fila = ctk.CTkFrame(self.scroll_rows, fg_color="#3a3a3a" if index % 2 == 0 else "#2e2e2e", height=34); fila.pack(fill="x", pady=2); fila.pack_propagate(False)
            self._celdas(fila, ((f"#{r[0]}", .08), (r[1], .43), (r[2], .13), (f"S/ {r[3]:.2f}", .16), (r[4], .20)))

    def descargar_plantilla(self):
        origen = resolver_recurso("templates/Plantilla_Importacion_Recursos_BAP.xlsx")
        ruta = filedialog.asksaveasfilename(defaultextension=".xlsx", initialfile=origen.name, filetypes=[("Excel", "*.xlsx")])
        if ruta: shutil.copy2(origen, ruta); messagebox.showinfo("Plantilla", f"Plantilla guardada en:\n{ruta}")

    def seleccionar_archivo(self):
        ruta = filedialog.askopenfilename(filetypes=[("Excel o CSV", "*.xlsx *.csv"), ("Excel", "*.xlsx"), ("CSV", "*.csv")])
        if not ruta: return
        try: filas = previsualizar_importacion(ruta, self.empresa_id)
        except Exception as exc: messagebox.showerror("Importación", str(exc)); return
        self.ruta_importacion = ruta; self.lbl_archivo.configure(text=Path(ruta).name)
        for w in self.preview_rows.winfo_children(): w.destroy()
        validas = sum(1 for f in filas if f["valido"]); invalidas = len(filas) - validas
        self.lbl_resumen.configure(text=f"{len(filas)} filas encontradas | {validas} válidas | {invalidas} con observaciones")
        self.btn_importar.configure(state="normal" if validas and self.can_edit else "disabled")
        for index, f in enumerate(filas):
            fila = ctk.CTkFrame(self.preview_rows, fg_color="#3a3a3a" if index % 2 == 0 else "#2e2e2e", height=38); fila.pack(fill="x", pady=2); fila.pack_propagate(False)
            estado = "Válida" if f["valido"] else f.get("errores", "Error")
            precio = f"S/ {f['precio']:.2f}" if f.get("precio") else "-"
            self._celdas(fila, ((str(f["fila"]), .08), (f["accion"], .14), (f.get("nombre", ""), .34), (f.get("proveedor", ""), .22), (precio, .12), (estado, .10)))

    def importar(self):
        if not self.ruta_importacion or not messagebox.askyesno("Confirmar importación", "¿Registrar todas las filas válidas de la vista previa?"): return
        try: resumen = ejecutar_importacion(self.ruta_importacion, self.empresa_id, self.usuario_id)
        except Exception as exc: messagebox.showerror("Importación", str(exc)); return
        self.cargar(); self.btn_importar.configure(state="disabled")
        messagebox.showinfo("Importación terminada", f"Filas válidas: {resumen['validas']}\nRecursos nuevos: {resumen['nuevos']}\nPrecios actualizados: {resumen['actualizados']}\nOfertas registradas: {resumen['ofertas']}\nFilas omitidas: {resumen['omitidos']}")

    def cargar_ofertas(self):
        for w in self.ofertas_rows.winfo_children(): w.destroy()
        recurso = self.recursos_dict.get(self.recurso_var.get())
        if not recurso: self.lbl_precio_actual.configure(text="Precio actual: -"); return
        self.lbl_precio_actual.configure(text=f"Precio actual: S/ {recurso[3]:.2f}")
        ofertas = obtener_ofertas_recurso(self.empresa_id, recurso[0])
        if not ofertas: ctk.CTkLabel(self.ofertas_rows, text="No existen ofertas importadas para este recurso.", text_color="#aab7c4").pack(pady=35); return
        for index, oferta in enumerate(ofertas):
            fila = ctk.CTkFrame(self.ofertas_rows, fg_color="#3a3a3a" if index % 2 == 0 else "#2e2e2e", height=42); fila.pack(fill="x", pady=2); fila.pack_propagate(False)
            valores = ((oferta[1], .25), (oferta[2] or "-", .14), (f"S/ {oferta[3]:.2f}", .12), (str(oferta[4] or "-"), .10), (str(oferta[5] if oferta[5] is not None else "-"), .10), (f"{oferta[6]} días" if oferta[6] is not None else "-", .11), (oferta[7], .10))
            self._celdas(fila, valores)
            boton = ctk.CTkButton(fila, text="Usar", width=58, height=27, fg_color=COLOR_TEAL, command=lambda oid=oferta[0], rid=recurso[0]: self.usar_oferta(rid, oid)); boton.place(relx=.92, rely=.16, relwidth=.07)
            if not self.can_edit: boton.configure(state="disabled")

    def usar_oferta(self, recurso_id, oferta_id):
        if not messagebox.askyesno("Actualizar precio", "¿Usar esta oferta como precio actual del recurso?"): return
        try: precio = aplicar_precio_oferta(self.empresa_id, recurso_id, oferta_id)
        except Exception as exc: messagebox.showerror("Precio", str(exc)); return
        self.cargar()
        seleccion = next((k for k, r in self.recursos_dict.items() if r[0] == recurso_id), None)
        if seleccion: self.recurso_var.set(seleccion)
        self.cargar_ofertas(); messagebox.showinfo("Precio actualizado", f"Nuevo precio: S/ {precio:.2f}")
