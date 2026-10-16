import customtkinter as ctk
import os
import sys
from dataclasses import replace
from PIL import Image
from database import crear_tablas, obtener_subtotales, obtener_apu, obtener_total
from views.proyectos import VistaProyectos
from views.recursos import VistaRecursos
from views.apu import VistaAPU
from views.partidas import VistaPartidas
from views.usuarios import VistaUsuarios
from views.dashboard import VistaDashboard
from views.terceros import VistaTerceros
from views.reportes import VistaReportes
from views.configuracion import VistaConfiguracion
from exportar_pdf import exportar_apu_pdf
from services.auth_service import autenticar, cambiar_password, cerrar_sesion
from services.business_service import empresa_principal
from services.offline_license import verificar_acceso
from views.activacion import VentanaActivacion
from tkinter import filedialog, messagebox
from brand import APP_NAME, APP_VERSION, COMPANY_NAME, COLOR_TEAL, COLOR_GOLD


def resolver_recurso(ruta_relativa):
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, ruta_relativa)


def cargar_isotipo(tamano):
    imagen = Image.open(resolver_recurso(os.path.join("assets", "bap_isotipo.png")))
    return ctk.CTkImage(light_image=imagen, dark_image=imagen, size=(tamano, tamano))

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class LoginWindow:
    def __init__(self):
        self.resultado = None
        self.root = ctk.CTk()
        self.root.title(f"Acceso - {APP_NAME}")
        self.root.geometry("420x410")
        self.root.resizable(False, False)

        self.root.eval('tk::PlaceWindow . center')

        self.logo_login = cargar_isotipo(68)
        ctk.CTkLabel(self.root, text="", image=self.logo_login).pack(pady=(18, 2))
        ctk.CTkLabel(self.root, text=APP_NAME, font=("Arial", 18, "bold"), text_color=COLOR_TEAL).pack(pady=(0, 3))
        ctk.CTkLabel(self.root, text=COMPANY_NAME, font=("Arial", 11, "italic"), text_color="#bdc3c7").pack(pady=(0, 15))

        ctk.CTkLabel(self.root, text="Por favor, ingresa tus credenciales para continuar", text_color="#ffffff", font=("Arial", 12, "bold")).pack(pady=2)
        self.txt_usuario = ctk.CTkEntry(self.root, font=("Arial",12), width=240, height=35, placeholder_text="Ingrese su usuario")
        self.txt_usuario.pack(pady=5)

        ctk.CTkLabel(self.root, text="Contraseña:", text_color="#ffffff", font=("Arial", 12, "bold")).pack(pady=2)
        self.txt_contraseña = ctk.CTkEntry(self.root, font=("Arial",12), width=240, height=35, placeholder_text="******", show="*")
        self.txt_contraseña.pack(pady=5)

        btn_ingresar =ctk.CTkButton(self.root, text="Iniciar Sesión", font=("Arial", 12,"bold"), fg_color="#2ecc71", text_color="white", hover_color="#27ae60", width=180, height=40, command=self.iniciar_sesion)
        btn_ingresar.pack(pady=25)
        self.root.bind("<Return>", lambda _evento: self.iniciar_sesion())

    def run(self):
        self.root.mainloop()
        return self.resultado

    def iniciar_sesion(self):
        usuario = self.txt_usuario.get()
        contraseña = self.txt_contraseña.get()

        sesion, error = autenticar(usuario, contraseña)
        if not sesion:
            messagebox.showerror("Error de autenticación", error)
            self.txt_contraseña.delete(0, "end")
            return
        if sesion.debe_cambiar_password:
            if not DialogoCambioPassword(self.root, sesion.id, contraseña).mostrar():
                cerrar_sesion(sesion)
                return
            sesion = replace(sesion, debe_cambiar_password=False)
        self.resultado = sesion
        self.root.destroy()


class DialogoCambioPassword:
    def __init__(self, parent, usuario_id, password_actual):
        self.usuario_id = usuario_id
        self.password_actual = password_actual
        self.exito = False
        self.ventana = ctk.CTkToplevel(parent)
        self.ventana.title("Cambiar contraseña inicial")
        self.ventana.geometry("420x330")
        self.ventana.resizable(False, False)
        self.ventana.transient(parent)
        self.ventana.grab_set()
        self.ventana.protocol("WM_DELETE_WINDOW", self.ventana.destroy)
        ctk.CTkLabel(
            self.ventana, text="Proteja su cuenta", font=("Arial", 19, "bold"),
            text_color="#3498db"
        ).pack(pady=(25, 8))
        ctk.CTkLabel(
            self.ventana,
            text="Cree una contraseña con 8 caracteres,\nmayúscula, minúscula y número.",
        ).pack(pady=5)
        self.nueva = ctk.CTkEntry(self.ventana, width=280, show="*", placeholder_text="Nueva contraseña")
        self.nueva.pack(pady=10)
        self.confirmacion = ctk.CTkEntry(self.ventana, width=280, show="*", placeholder_text="Confirmar contraseña")
        self.confirmacion.pack(pady=5)
        ctk.CTkButton(self.ventana, text="Guardar y continuar", command=self.guardar).pack(pady=22)

    def mostrar(self):
        self.ventana.wait_window()
        return self.exito

    def guardar(self):
        nueva = self.nueva.get()
        if nueva != self.confirmacion.get():
            messagebox.showerror("Contraseñas diferentes", "La confirmación no coincide.", parent=self.ventana)
            return
        try:
            cambiar_password(self.usuario_id, self.password_actual, nueva)
        except ValueError as exc:
            messagebox.showerror("Contraseña no válida", str(exc), parent=self.ventana)
            return
        self.exito = True
        self.ventana.destroy()

class AppAPU(ctk.CTk):

    def __init__(self, sesion, estado_licencia):
        super().__init__()
        self.sesion = sesion
        self.empresa = empresa_principal(sesion.id)
        self.estado_licencia = estado_licencia
        if not self.empresa:
            raise RuntimeError("El usuario no tiene una empresa asignada.")
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
        if self.sesion.puede(permiso):
            ctk.CTkButton(self.menu, text=texto, command=comando).pack(pady=7)

    def mostrar_dashboard(self):
        self.limpiar_vista()
        self.vista_actual = VistaDashboard(self.contenedor, self.empresa[0])
        self.vista_actual.pack(fill="both", expand=True)

    def logout(self):
        cerrar_sesion(self.sesion)
        self.solicito_cerrar_sesion = True
        self.destroy()

    def exportar_pdf(self):
        if not self.sesion.puede("apu.exportar"):
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

        datos = obtener_apu(proyecto_id)
        total = obtener_total(proyecto_id)
        subtotales = obtener_subtotales(proyecto_id)

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
            exportar_apu_pdf(nombre_proyecto, datos, subtotales, total, ruta_guardado)
        
            # 3. Mostrar mensaje confirmando la ruta real elegida
            messagebox.showinfo("PDF generado", f"El archivo se guardó correctamente en:\n{ruta_guardado}")
        except Exception as e:
            messagebox.showerror("Error al guardar", f"No se pudo generar el archivo PDF: {str(e)}")

    def limpiar_vista(self):
        if self.vista_actual:
            self.vista_actual.destroy()

    def mostrar_proyectos(self):
        self.limpiar_vista()
        self.vista_actual = VistaProyectos(self.contenedor, self.sesion.puede("proyectos.editar"), self.empresa[0])
        self.vista_actual.pack(fill="both", expand=True)

    def mostrar_recursos(self):
        self.limpiar_vista()
        self.vista_actual = VistaRecursos(
            self.contenedor, self.sesion.puede("recursos.editar"),
            self.empresa[0], self.sesion.id,
        )
        self.vista_actual.pack(fill="both", expand=True)

    def mostrar_apu(self):
        self.limpiar_vista()
        self.vista_actual = VistaAPU(
            self.contenedor,
            can_edit=self.sesion.puede("apu.editar"),
            can_export=self.sesion.puede("apu.exportar"),
            empresa_id=self.empresa[0],
        )
        self.vista_actual.pack(fill="both", expand=True)

    def mostrar_partidas(self):
        self.limpiar_vista()
        self.vista_actual = VistaPartidas(self.contenedor, self.sesion.puede("partidas.usar"), self.empresa[0])
        self.vista_actual.pack(fill="both", expand=True)

    def mostrar_usuarios(self):
        self.limpiar_vista()
        self.vista_actual = VistaUsuarios(self.contenedor, self.sesion)
        self.vista_actual.pack(fill="both", expand=True)

    def mostrar_terceros(self):
        self.limpiar_vista()
        self.vista_actual = VistaTerceros(
            self.contenedor, self.sesion, self.empresa[0],
            self.sesion.puede("clientes.editar") or self.sesion.puede("proveedores.editar")
        )
        self.vista_actual.pack(fill="both", expand=True)

    def mostrar_reportes(self):
        self.limpiar_vista()
        self.vista_actual = VistaReportes(
            self.contenedor, self.empresa[0],
            self.sesion.puede("reportes.exportar"), self.sesion.puede("auditoria.ver")
        )
        self.vista_actual.pack(fill="both", expand=True)

    def mostrar_configuracion(self):
        self.limpiar_vista()
        self.vista_actual = VistaConfiguracion(
            self.contenedor, self.sesion, self.empresa,
            self.sesion.puede("configuracion.gestionar"),
            self.sesion.puede("respaldos.gestionar"),
        )
        self.vista_actual.pack(fill="both", expand=True)

if __name__ == "__main__":
    crear_tablas()
    estado_actual = verificar_acceso()
    if not estado_actual.permitido:
        if not VentanaActivacion(estado_actual).run():
            raise SystemExit(0)
        estado_actual = verificar_acceso()
        if not estado_actual.permitido:
            raise SystemExit(1)
    while True:
        sesion_actual = LoginWindow().run()
        if not sesion_actual:
            break
        app = AppAPU(sesion_actual, estado_actual)
        app.mainloop()
        if not app.solicito_cerrar_sesion:
            cerrar_sesion(sesion_actual)
            break
