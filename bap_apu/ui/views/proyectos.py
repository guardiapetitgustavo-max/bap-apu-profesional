import customtkinter as ctk
from tkinter import messagebox

class VistaProyectos(ctk.CTkFrame):

    def __init__(self, parent, servicios, ctx):
        super().__init__(parent)
        self.servicios = servicios
        self.ctx = ctx
        self.can_edit = ctx.puede("proyectos.editar")

        ctk.CTkLabel(self, text="GESTIÓN DE PROYECTOS", font=("Arial", 22, "bold")).pack(pady=15)

        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.pack(fill="both", expand=True, padx=20, pady=10)
        
        self.main_container.columnconfigure(0, weight=1) # Formulario (Más angosto)
        self.main_container.columnconfigure(1, weight=2) # Tabla (Más ancho)

        self.form_frame = ctk.CTkFrame(self.main_container, width=300)
        self.form_frame.grid(row=0, column=0, sticky="nsw", padx=(0, 15), pady=5)
        
        ctk.CTkLabel(self.form_frame, text="Nuevo Proyecto", font=("Arial", 14, "bold")).pack(pady=10)

        self.nombre = ctk.CTkEntry(self.form_frame, placeholder_text="Nombre del proyecto", width=220)
        self.nombre.pack(pady=15)

        self.btn_guardar = ctk.CTkButton(
            self.form_frame, 
            text="➕ Crear Proyecto", 
            command=self.guardar, 
            fg_color="#1f538d", 
            hover_color="#14375e",
            width=220
        )
        self.btn_guardar.pack(pady=10)
        if not self.can_edit:
            self.btn_guardar.configure(state="disabled", text="Solo lectura")

        self.table_container = ctk.CTkFrame(self.main_container)
        self.table_container.grid(row=0, column=1, sticky="nsew", pady=5)
        
        self.header_frame = ctk.CTkFrame(self.table_container, fg_color="#2b2b2b", height=35)
        self.header_frame.pack(fill="x", side="top")
        self.header_frame.pack_propagate(False)

        headers = [("ID", 0.15), ("Nombre del Proyecto", 0.65), ("Acciones", 0.2)]
        for text, weight in headers:
            lbl = ctk.CTkLabel(self.header_frame, text=text, font=("Arial", 12, "bold"), text_color="white", anchor="w")
            pos_x = sum([h[1] for h in headers[:headers.index((text, weight))]]) + 0.02
            lbl.place(relx=pos_x, rely=0.2, relwidth=weight)

        self.scroll_rows = ctk.CTkScrollableFrame(self.table_container, fg_color="transparent")
        self.scroll_rows.pack(fill="both", expand=True, padx=2, pady=2)

        self.cargar()

    @staticmethod
    def _error(exc):
        if isinstance(exc, PermissionError):
            messagebox.showerror("Acceso denegado", str(exc))
        else:
            messagebox.showerror("Proyecto", str(exc))

    def guardar(self):
        nombre_val = self.nombre.get().strip()
        
        if not nombre_val:
            messagebox.showwarning("Campo vacío", "Por favor, ingresa el nombre del proyecto.")
            return

        try:
            self.servicios.proyectos.crear(self.ctx, nombre_val)
        except (ValueError, PermissionError) as exc:
            self._error(exc)
            return
        
        self.nombre.delete(0, "end")
        
        self.cargar()
        messagebox.showinfo("Éxito", "Proyecto creado correctamente.")

    def borrar_proyecto(self, proyecto_id):
        if messagebox.askyesno("Confirmar", "¿Estás seguro de eliminar este proyecto y todos sus registros asociados?"):
            try:
                self.servicios.proyectos.eliminar(self.ctx, proyecto_id)
            except (ValueError, PermissionError) as exc:
                self._error(exc)
                return
            self.cargar()

    def cargar(self):
        for widget in self.scroll_rows.winfo_children():
            widget.destroy()

        proyectos_bd = self.servicios.proyectos.listar(self.ctx)

        for index, p in enumerate(proyectos_bd):
            bg_row = "#3a3a3a" if index % 2 == 0 else "#2e2e2e"
            
            row_frame = ctk.CTkFrame(self.scroll_rows, fg_color=bg_row, height=38, corner_radius=4)
            row_frame.pack(fill="x", pady=2)
            row_frame.pack_propagate(False)

            lbl_id = ctk.CTkLabel(row_frame, text=f" #{p[0]}", font=("Arial", 12), anchor="w")
            lbl_id.place(relx=0.02, rely=0.2, relwidth=0.15)

            lbl_nombre = ctk.CTkLabel(row_frame, text=p[1], font=("Arial", 12), anchor="w")
            lbl_nombre.place(relx=0.17, rely=0.2, relwidth=0.63)

            btn_eliminar = ctk.CTkButton(
                row_frame, 
                text="🗑️", 
                width=30, 
                height=24,
                fg_color="#bf360c", 
                hover_color="#870000",
                command=lambda id_proy=p[0]: self.borrar_proyecto(id_proy)
            )
            if self.can_edit:
                btn_eliminar.place(relx=0.82, rely=0.18, relwidth=0.15)
