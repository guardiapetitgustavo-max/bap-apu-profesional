import customtkinter as ctk
from database import (
    obtener_proyectos, 
    obtener_recursos, 
    insertar_detalle, 
    obtener_apu, 
    obtener_subtotales, 
    obtener_total,
    eliminar_detalle_apu
)
from tkinter import messagebox

class VistaAPU(ctk.CTkFrame):

    def __init__(self, parent, can_edit=True, can_export=True, empresa_id=None):
        super().__init__(parent)
        self.can_edit = can_edit
        self.can_export = can_export
        self.empresa_id = empresa_id

        self.parent_app = parent.master

        self.proyectos_dict = {}
        self.recursos_dict = {}

        self.top_frame = ctk.CTkFrame(self, height=70)
        self.top_frame.pack(fill="x", padx=20, pady=(15, 5))
        self.top_frame.pack_propagate(False)

        ctk.CTkLabel(self.top_frame, text="Seleccione Proyecto:", font=("Arial", 12, "bold")).pack(side="left", padx=15)
        
        self.proyecto_var = ctk.StringVar(value="Seleccionar...")
        self.cb_proyectos = ctk.CTkOptionMenu(self.top_frame, variable=self.proyecto_var, command=self.cambiar_proyecto, width=250)
        self.cb_proyectos.pack(side="left", padx=5)

        self.btn_pdf = ctk.CTkButton(
            self.top_frame, 
            text="🖨️ Exportar APU a PDF", 
            command=self.invocar_pdf_global,
            font=("Arial", 12, "bold"), 
            fg_color="#b71c1c", 
            hover_color="#d32f2f",
            text_color="white",
            height=35,
            width=180,
            corner_radius=8,
            border_width=1,
            border_color="#7f0000"
        )
        self.btn_pdf.pack(side="right", padx=15)
        if not self.can_export:
            self.btn_pdf.configure(state="disabled", text="PDF no permitido")

        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.pack(fill="both", expand=True, padx=20, pady=10)
        
        self.main_container.columnconfigure(0, weight=1) # Formulario
        self.main_container.columnconfigure(1, weight=3) # Tabla Desglose

        self.form_frame = ctk.CTkFrame(self.main_container, width=280)
        self.form_frame.grid(row=0, column=0, sticky="nsw", padx=(0, 15), pady=5)
        
        ctk.CTkLabel(self.form_frame, text="Asignar Recurso al APU", font=("Arial", 14, "bold")).pack(pady=10)

        ctk.CTkLabel(self.form_frame, text="Buscar Recurso Base:").pack(pady=(5,0))
        self.recurso_var = ctk.StringVar(value="Seleccionar recurso...")
        self.cb_recursos = ctk.CTkOptionMenu(self.form_frame, variable=self.recurso_var, width=220)
        self.cb_recursos.pack(pady=5)

        self.cantidad = ctk.CTkEntry(self.form_frame, placeholder_text="Cantidad / Rendimiento", width=220)
        self.cantidad.pack(pady=15)

        self.btn_agregar = ctk.CTkButton(
            self.form_frame, 
            text="➕ Añadir al APU", 
            command=self.guardar_item, 
            fg_color="#1f538d", 
            hover_color="#14375e",
            width=220
        )
        self.btn_agregar.pack(pady=10)
        if not self.can_edit:
            self.btn_agregar.configure(state="disabled", text="Solo lectura")

        self.table_container = ctk.CTkFrame(self.main_container)
        self.table_container.grid(row=0, column=1, sticky="nsew", pady=5)
        
        self.header_frame = ctk.CTkFrame(self.table_container, fg_color="#2b2b2b", height=35)
        self.header_frame.pack(fill="x", side="top")
        self.header_frame.pack_propagate(False)

        headers = [("Descripción del Recurso", 0.32), ("Tipo", 0.16), ("Unidad", 0.12), ("Precio", 0.12), ("Cantidad", 0.11), ("Parcial", 0.12)]
        for text, weight in headers:
            lbl = ctk.CTkLabel(self.header_frame, text=text, font=("Arial", 12, "bold"), text_color="white", anchor="w")
            pos_x = sum([h[1] for h in headers[:headers.index((text, weight))]]) + 0.01
            lbl.place(relx=pos_x, rely=0.2, relwidth=weight)

        self.scroll_rows = ctk.CTkScrollableFrame(self.table_container, fg_color="transparent")
        self.scroll_rows.pack(fill="both", expand=True, padx=2, pady=2)

        self.summary_frame = ctk.CTkFrame(self.table_container, fg_color="#212121", height=45)
        self.summary_frame.pack(fill="x", side="bottom")
        
        self.lbl_totales = ctk.CTkLabel(
            self.summary_frame, 
            text="Mano de Obra: S/ 0.00  |  Materiales: S/ 0.00  |  Equipos: S/ 0.00  |  TOTAL: S/ 0.00", 
            font=("Arial", 12, "bold"), 
            text_color="#81c784"
        )
        self.lbl_totales.pack(pady=10, padx=15, side="right")

        self.inicializar_selectores()

    def inicializar_selectores(self):
        """Pobla los menús desplegables con datos limpios de la BD."""
        proyectos = obtener_proyectos(self.empresa_id)
        self.proyectos_dict = {p[1]: p[0] for p in proyectos}
        if self.proyectos_dict:
            self.cb_proyectos.configure(values=list(self.proyectos_dict.keys()))
        
        recursos = obtener_recursos(self.empresa_id)
        # Estructura: { "Cemento Sol (BL) - S/ 25.00": (id, nombre, unidad, precio, tipo) }
        self.recursos_dict = {f"{r[1]} ({r[2]}) - S/ {r[3]:.2f}": r for r in recursos}
        if self.recursos_dict:
            self.cb_recursos.configure(values=list(self.recursos_dict.keys()))

    def obtener_id_proyecto(self):
        """Retorna el ID numérico del proyecto seleccionado."""
        return self.proyectos_dict.get(self.proyecto_var.get(), None)

    def cambiar_proyecto(self, nombre_proyecto):
        """Evento al cambiar de proyecto en el menú superior."""
        self.cargar_tabla_apu()

    def invocar_pdf_global(self):
        """Llama al método exportar_pdf definido en la raíz del main.py."""
        if hasattr(self.parent_app, 'exportar_pdf'):
            self.parent_app.exportar_pdf()

    def guardar_item(self):
        proyecto_id = self.obtener_id_proyecto()
        if not proyecto_id:
            messagebox.showwarning("Falta Proyecto", "Por favor, seleccione un proyecto del menú superior.")
            return

        recurso_seleccionado = self.recurso_var.get()
        datos_recurso = self.recursos_dict.get(recurso_seleccionado, None)
        if not datos_recurso:
            messagebox.showwarning("Falta Recurso", "Por favor, seleccione un recurso de la lista.")
            return

        try:
            cant_val = float(self.cantidad.get())
            if cant_val <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Cantidad Inválida", "Ingrese un valor numérico mayor a cero.")
            return

        # Desempaquetar datos del recurso base: (id, nombre, unidad, precio, tipo)
        _, nombre, unidad, precio, tipo = datos_recurso

        # Insertar fila de desglose en el APU
        insertar_detalle(proyecto_id, nombre, unidad, precio, cant_val, tipo)
        
        # Limpiar entrada y refrescar
        self.cantidad.delete(0, "end")
        self.cargar_tabla_apu()

    def borrar_item_apu(self, detalle_id):
        """Muestra una confirmación y elimina un solo recurso de la tabla APU."""
        confirmacion = messagebox.askyesno(
        "Confirmar Eliminación", 
            "¿Está seguro de que desea eliminar este recurso del desglose APU?"
        )
        
        if confirmacion:  # Si el usuario presiona "Sí"
            eliminar_detalle_apu(detalle_id)
            self.cargar_tabla_apu()

    def cargar_tabla_apu(self):

        for widget in self.scroll_rows.winfo_children():
            widget.destroy()

        proyecto_id = self.obtener_id_proyecto()
        if not proyecto_id:
            return

        # Obtener análisis del proyecto
        items_apu = obtener_apu(proyecto_id)

        headers_pesos = [0.32,0.16, 0.12, 0.12, 0.11, 0.12]

        for idx, item in enumerate(items_apu):
            # item: (id, nombre, unidad, precio, cantidad, parcial, tipo)
            bg_row = "#3a3a3a" if idx % 2 == 0 else "#2e2e2e"
            
            row_frame = ctk.CTkFrame(self.scroll_rows, fg_color=bg_row, height=35, corner_radius=4)
            row_frame.pack(fill="x", pady=2, padx=5)
            row_frame.pack_propagate(False)

            celdas_datos = [
                f" {item[1]}",
                f" {item[6]}",
                f" {item[2]}",
                f" S/ {item[3]:.2f}",
                f" {item[4]}",
                f" S/ {item[5]:.2f}"
            ]
            
            pos_x = 0.01
            for i, text in enumerate(celdas_datos):
                weight = headers_pesos[i]
                lbl = ctk.CTkLabel(row_frame, text=text, font=("Arial", 11), anchor="w")
                lbl.place(relx=pos_x, rely=0.15, relwidth=weight - 0.01)
                pos_x += weight

            btn_del = ctk.CTkButton(
                row_frame, 
                text="❌",
                width=26, 
                height=24,
                fg_color="#b71c1c",
                hover_color="#e53935",
                text_color="white",
                font=("Arial", 10, "bold"),
                corner_radius=4,
                command=lambda d_id=item[0]: self.borrar_item_apu(d_id)
            )
            if self.can_edit:
                btn_del.place(relx=0.95, rely=0.15, relwidth=0.04)

        sub = obtener_subtotales(proyecto_id)
        total = obtener_total(proyecto_id)
        
        texto_resumen = (
            f"Mano de Obra: S/ {sub.get('Mano de Obra', 0):.2f}  |  "
            f"Materiales: S/ {sub.get('Materiales', 0):.2f}  |  "
            f"Equipo: S/ {sub.get('Equipo', 0):.2f}  |  "
            f"TOTAL: S/ {total:.2f}"
        )
        self.lbl_totales.configure(text=texto_resumen)
