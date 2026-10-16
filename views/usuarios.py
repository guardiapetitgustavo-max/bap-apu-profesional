import customtkinter as ctk
from tkinter import messagebox

from services.auth_service import (
    cambiar_estado_usuario,
    crear_usuario,
    listar_roles,
    listar_usuarios,
)


class VistaUsuarios(ctk.CTkFrame):
    def __init__(self, parent, sesion):
        super().__init__(parent)
        self.sesion = sesion
        self.roles = {}
        ctk.CTkLabel(self, text="GESTIÓN DE USUARIOS", font=("Arial", 22, "bold")).pack(pady=15)
        cuerpo = ctk.CTkFrame(self, fg_color="transparent")
        cuerpo.pack(fill="both", expand=True, padx=20, pady=5)
        cuerpo.grid_columnconfigure(1, weight=1)
        cuerpo.grid_rowconfigure(0, weight=1)

        form = ctk.CTkFrame(cuerpo, width=280)
        form.grid(row=0, column=0, sticky="ns", padx=(0, 15))
        ctk.CTkLabel(form, text="Nuevo usuario", font=("Arial", 14, "bold")).pack(pady=12)
        self.usuario = ctk.CTkEntry(form, width=230, placeholder_text="Nombre de usuario")
        self.usuario.pack(pady=7)
        self.nombre = ctk.CTkEntry(form, width=230, placeholder_text="Nombre completo")
        self.nombre.pack(pady=7)
        self.password = ctk.CTkEntry(form, width=230, show="*", placeholder_text="Contraseña temporal")
        self.password.pack(pady=7)
        self.rol_var = ctk.StringVar(value="Seleccionar rol...")
        self.cb_rol = ctk.CTkOptionMenu(form, variable=self.rol_var, width=230)
        self.cb_rol.pack(pady=9)
        ctk.CTkButton(form, text="Crear usuario", command=self.guardar, width=230).pack(pady=14)

        tabla = ctk.CTkFrame(cuerpo)
        tabla.grid(row=0, column=1, sticky="nsew")
        cab = ctk.CTkFrame(tabla, fg_color="#2b2b2b", height=35)
        cab.pack(fill="x"); cab.pack_propagate(False)
        columnas=[("Usuario",.18),("Nombre",.30),("Rol",.20),("Estado",.12),("Acción",.20)]
        x=.01
        for texto,ancho in columnas:
            ctk.CTkLabel(cab,text=texto,font=("Arial",11,"bold"),anchor="w").place(relx=x,rely=.2,relwidth=ancho)
            x+=ancho
        self.filas=ctk.CTkScrollableFrame(tabla,fg_color="transparent")
        self.filas.pack(fill="both",expand=True)
        self.inicializar()

    def inicializar(self):
        self.roles={nombre:identificador for identificador,nombre in listar_roles()}
        self.cb_rol.configure(values=list(self.roles))
        self.cargar()

    def guardar(self):
        rol_id=self.roles.get(self.rol_var.get())
        if not rol_id:
            messagebox.showwarning("Falta rol","Seleccione un rol para el usuario."); return
        try:
            crear_usuario(self.sesion.id,self.usuario.get(),self.nombre.get(),self.password.get(),rol_id)
        except ValueError as exc:
            messagebox.showerror("No se pudo crear",str(exc)); return
        for campo in (self.usuario,self.nombre,self.password): campo.delete(0,"end")
        self.cargar(); messagebox.showinfo("Éxito","Usuario creado. Deberá cambiar su contraseña al ingresar.")

    def cargar(self):
        for widget in self.filas.winfo_children(): widget.destroy()
        for indice,u in enumerate(listar_usuarios()):
            fondo="#3a3a3a" if indice%2==0 else "#2e2e2e"
            fila=ctk.CTkFrame(self.filas,fg_color=fondo,height=38); fila.pack(fill="x",pady=2); fila.pack_propagate(False)
            valores=[u[1],u[2],u[3],"Activo" if u[4] else "Inactivo"]
            pesos=[.18,.30,.20,.12]; x=.01
            for valor,ancho in zip(valores,pesos):
                ctk.CTkLabel(fila,text=valor,font=("Arial",10),anchor="w").place(relx=x,rely=.2,relwidth=ancho-.01); x+=ancho
            nuevo_estado=not bool(u[4])
            ctk.CTkButton(
                fila,text="Activar" if nuevo_estado else "Desactivar",width=90,height=25,
                fg_color="#2e7d32" if nuevo_estado else "#b71c1c",
                command=lambda uid=u[0],estado=nuevo_estado:self.cambiar_estado(uid,estado)
            ).place(relx=.82,rely=.16,relwidth=.16)

    def cambiar_estado(self,usuario_id,activo):
        try: cambiar_estado_usuario(self.sesion.id,usuario_id,activo)
        except ValueError as exc: messagebox.showerror("Acción no permitida",str(exc)); return
        self.cargar()
