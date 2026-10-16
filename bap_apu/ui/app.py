import customtkinter as ctk
from tkinter import filedialog, messagebox

from bap_apu.brand import APP_NAME, APP_VERSION, COLOR_TEAL, COLOR_GOLD
from bap_apu.ui.imagenes import cargar_isotipo
from bap_apu.ui.views.apu import VistaAPU
from bap_apu.ui.views.configuracion import VistaConfiguracion
from bap_apu.ui.views.dashboard import VistaDashboard
from bap_apu.ui.views.partidas import VistaPartidas
from bap_apu.ui.views.proyectos import VistaProyectos
from bap_apu.ui.views.recursos import VistaRecursos
from bap_apu.ui.views.reportes import VistaReportes
from bap_apu.ui.views.terceros import VistaTerceros
from bap_apu.ui.views.usuarios import VistaUsuarios


class AppAPU(ctk.CTk):

    def __init__(self, servicios, sesion, ctx, estado_licencia):
        super().__init__()
        self.servicios = servicios
        self.sesion = sesion
        self.ctx = ctx
        self.estado_licencia = estado_licencia
        self.solicito_cerrar_sesion = False

        self.title(f"{APP_NAME} {APP_VERSION}")
        self.geometry("1280x760")
        self.minsize(1100, 680)

        # ----- Layout principal -----
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # ----- Menú lateral -----
        self.menu = ctk.CTkScrollableFrame(self, width=220)
        self.menu.grid(row=0, column=0, sticky="ns")

        self.logo_menu = cargar_isotipo(56)
        ctk.CTkLabel(self.menu, text="", image=self.logo_menu).pack(pady=(18, 2))
        ctk.CTkLabel(self.menu, text="BAP APU", font=("Arial", 18, "bold"), text_color=COLOR_TEAL).pack(pady=(0, 2))
        ctk.CTkLabel(self.menu, text=f"Profesional {APP_VERSION}", font=("Arial", 10, "bold"), text_color=COLOR_GOLD).pack(pady=(0, 14))

        ctk.CTkLabel(
            self.menu, text=f"{sesion.nombre_completo}\n{sesion.rol}",
            font=("Arial", 11), text_color="#b0bec5"
        ).pack(pady=(0, 15))
        ctk.CTkLabel(
            self.menu, text=estado_licencia.mensaje,
            font=("Arial", 10, "bold"),
            text_color="#81c784" if estado_licencia.modo == "LICENCIA" else "#ffcc80",
            wraplength=190,
        ).pack(pady=(0, 10))

        self._agregar_boton("Dashboard", self.mostrar_dashboard, "dashboard.ver")
        self._agregar_boton("Proyectos", self.mostrar_proyectos, "proyectos.ver")
        self._agregar_boton("Recursos", self.mostrar_recursos, "recursos.ver")
        self._agregar_boton("Biblioteca de Partidas", self.mostrar_partidas, "partidas.ver")
        self._agregar_boton("APU", self.mostrar_apu, "apu.ver")
        self._agregar_boton("Clientes y Proveedores", self.mostrar_terceros, "clientes.ver")
        self._agregar_boton("Reportes y Auditoría", self.mostrar_reportes, "reportes.ver")
        self._agregar_boton("Usuarios", self.mostrar_usuarios, "usuarios.gestionar")
        self._agregar_boton("Empresa y Licencia", self.mostrar_configuracion, "licencias.ver")
        ctk.CTkButton(
            self.menu, text="Cerrar sesión", command=self.logout,
            fg_color="#b71c1c", hover_color="#7f0000"
        ).pack(pady=20)

        self.contenedor = ctk.CTkFrame(self)
        self.contenedor.grid(row=0, column=1, sticky="nsew")

        self.vista_actual = None

        self.mostrar_dashboard()

    def _agregar_boton(self, texto, comando, permiso):
        if self.ctx.puede(permiso):
            ctk.CTkButton(self.menu, text=texto, command=comando).pack(pady=7)

    def mostrar_dashboard(self):
        self.limpiar_vista()
        self._mostrar(VistaDashboard)

    def logout(self):
        self.servicios.auth.cerrar_sesion(self.sesion)
        self.solicito_cerrar_sesion = True
        self.destroy()

    def exportar_pdf(self):
        if not self.ctx.puede("apu.exportar"):
            messagebox.showerror("Acceso denegado", "Su rol no permite exportar APU.")
            return
        if not isinstance(self.vista_actual, VistaAPU):
            messagebox.showwarning("Cambio de Vista", "Debes estar en la pestaña APU para exportar este proyecto.")
            return

        proyecto_id = self.vista_actual.obtener_id_proyecto()
        nombre_proyecto = self.vista_actual.proyecto_var.get()

        if not proyecto_id or nombre_proyecto == "Seleccionar...":
            messagebox.showwarning("Falta Selección", "Por favor, seleccione un proyecto válido primero.")
            return

        try:
            datos = self.servicios.apu.detalle(self.ctx, proyecto_id)
        except (ValueError, PermissionError) as e:
            messagebox.showerror("Acceso denegado" if isinstance(e, PermissionError) else "Proyecto", str(e))
            return

        if not datos:
            messagebox.showwarning("Sin Datos", "Este proyecto no tiene recursos asignados en el APU.")
            return

        # --- AQUÍ INICIA EL CAMBIO ---
        # 1. Abrir ventana para que el usuario elija dónde guardar
        ruta_guardado = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("Archivos PDF", "*.pdf")],
            title="Seleccionar dónde guardar el PDF",
            initialfile=f"APU_{nombre_proyecto}.pdf" # Sugiere el nombre dinámico
        )
    
        # Si el usuario cierra la ventana o presiona cancelar, detenemos el proceso
        if not ruta_guardado:
            return

        try:
            # 2. Pasar 'ruta_guardado' como un nuevo argumento a tu función generadora
            self.servicios.reportes.exportar_apu_pdf(self.ctx, proyecto_id, nombre_proyecto, ruta_guardado)
        
            # 3. Mostrar mensaje confirmando la ruta real elegida
            messagebox.showinfo("PDF generado", f"El archivo se guardó correctamente en:\n{ruta_guardado}")
        except Exception as e:
            messagebox.showerror("Error al guardar", f"No se pudo generar el archivo PDF: {str(e)}")

    def limpiar_vista(self):
        if self.vista_actual:
            self.vista_actual.destroy()
            self.vista_actual = None

    def _mostrar(self, clase):
        try:
            vista = clase(self.contenedor, self.servicios, self.ctx)
        except PermissionError as e:
            messagebox.showerror("Acceso denegado", str(e))
            return
        self.vista_actual = vista
        vista.pack(fill="both", expand=True)

    def mostrar_proyectos(self):
        self.limpiar_vista()
        self._mostrar(VistaProyectos)

    def mostrar_recursos(self):
        self.limpiar_vista()
        self._mostrar(VistaRecursos)

    def mostrar_apu(self):
        self.limpiar_vista()
        self._mostrar(VistaAPU)

    def mostrar_partidas(self):
        self.limpiar_vista()
        self._mostrar(VistaPartidas)

    def mostrar_usuarios(self):
        self.limpiar_vista()
        self._mostrar(VistaUsuarios)

    def mostrar_terceros(self):
        self.limpiar_vista()
        self._mostrar(VistaTerceros)

    def mostrar_reportes(self):
        self.limpiar_vista()
        self._mostrar(VistaReportes)

    def mostrar_configuracion(self):
        self.limpiar_vista()
        self._mostrar(VistaConfiguracion)
