import customtkinter as ctk
from dataclasses import replace
from tkinter import messagebox

from bap_apu.brand import APP_NAME, COMPANY_NAME, COLOR_TEAL
from bap_apu.ui.imagenes import cargar_isotipo


class LoginWindow:
    def __init__(self, servicios):
        self.servicios = servicios
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

        sesion, error = self.servicios.auth.autenticar(usuario, contraseña)
        if not sesion:
            messagebox.showerror("Error de autenticación", error)
            self.txt_contraseña.delete(0, "end")
            return
        if sesion.debe_cambiar_password:
            if not DialogoCambioPassword(self.root, self.servicios, sesion.id, contraseña).mostrar():
                self.servicios.auth.cerrar_sesion(sesion)
                return
            sesion = replace(sesion, debe_cambiar_password=False)
        self.resultado = sesion
        self.root.destroy()


class DialogoCambioPassword:
    def __init__(self, parent, servicios, usuario_id, password_actual):
        self.servicios = servicios
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
            self.servicios.auth.cambiar_password(self.usuario_id, self.password_actual, nueva)
        except ValueError as exc:
            messagebox.showerror("Contraseña no válida", str(exc), parent=self.ventana)
            return
        self.exito = True
        self.ventana.destroy()
