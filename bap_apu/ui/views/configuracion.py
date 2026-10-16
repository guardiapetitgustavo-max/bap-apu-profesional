import customtkinter as ctk
from tkinter import filedialog,messagebox
from bap_apu.services.actualizaciones import consultar_actualizacion
from bap_apu.licensing.offline_license import codigo_equipo
from bap_apu.brand import APP_VERSION, APP_NAME, COMPANY_NAME, WHATSAPP, EMAIL, WEBSITE, COLOR_TEAL


class VistaConfiguracion(ctk.CTkFrame):
    def __init__(self,parent,servicios,ctx):
        super().__init__(parent); self.servicios=servicios; self.ctx=ctx
        empresa=servicios.empresa.empresa_principal(ctx.usuario_id); self.empresa=empresa
        can_edit=ctx.puede("configuracion.gestionar"); can_backup=ctx.puede("respaldos.gestionar")
        ctk.CTkLabel(self,text="EMPRESA, LICENCIA Y RESPALDOS",font=("Arial",22,"bold")).pack(pady=15)
        tabs=ctk.CTkTabview(self); tabs.pack(fill="both",expand=True,padx=20,pady=(0,20))
        emp=tabs.add("Empresa"); self.campos={}
        datos=[("ruc","RUC",empresa[1]),("razon","Razón social",empresa[2]),("comercial","Nombre comercial",empresa[3]),("direccion","Dirección",empresa[4]),("telefono","Teléfono",empresa[5]),("email","Email",empresa[6])]
        for clave,label,valor in datos:
            fila=ctk.CTkFrame(emp,fg_color="transparent");fila.pack(fill="x",padx=30,pady=5);ctk.CTkLabel(fila,text=label,width=150,anchor="w").pack(side="left");e=ctk.CTkEntry(fila,width=420);e.insert(0,valor or "");e.pack(side="left");self.campos[clave]=e
        b=ctk.CTkButton(emp,text="Guardar empresa",command=self.guardar);b.pack(pady=18)
        if not can_edit:b.configure(state="disabled")
        lic=tabs.add("Licencia")
        ctk.CTkLabel(lic,text="LICENCIA Y CÓDIGO DEL EQUIPO",font=("Arial",18,"bold")).pack(pady=(25,10))
        self.lbl_licencia=ctk.CTkLabel(lic,text="",font=("Arial",14),justify="left")
        self.lbl_licencia.pack(pady=8)
        ctk.CTkLabel(lic,text="Envíe este código junto con el RUC al vendedor:").pack(pady=(16,5))
        fila_codigo=ctk.CTkFrame(lic,fg_color="transparent");fila_codigo.pack(pady=5)
        self.codigo_pc=ctk.CTkEntry(fila_codigo,width=350,justify="center",font=("Consolas",14,"bold"))
        self.codigo_pc.insert(0,codigo_equipo());self.codigo_pc.configure(state="readonly");self.codigo_pc.pack(side="left",padx=5)
        ctk.CTkButton(fila_codigo,text="Copiar código",width=120,command=self.copiar_codigo).pack(side="left",padx=5)
        ctk.CTkButton(lic,text="Activar ahora / Importar .apulic",width=260,height=40,fg_color="#2e7d32",hover_color="#1b5e20",command=self.importar_licencia).pack(pady=18)
        self.refrescar_licencia()
        resp=tabs.add("Respaldos");ctk.CTkLabel(resp,text="Cree o restaure una copia verificable de la base de datos.").pack(pady=(45,15));br=ctk.CTkButton(resp,text="Crear respaldo ahora",command=self.respaldar);br.pack(pady=6)
        brest=ctk.CTkButton(resp,text="Restaurar respaldo",command=self.restaurar,fg_color="#b36b00",hover_color="#8c5400");brest.pack(pady=6)
        if not can_backup:br.configure(state="disabled")
        if not can_backup:brest.configure(state="disabled")
        sistema=tabs.add("Sistema")
        ctk.CTkLabel(sistema,text=f"{APP_NAME}\nVersión {APP_VERSION}",font=("Arial",18,"bold"),text_color=COLOR_TEAL).pack(pady=(45,10))
        ctk.CTkLabel(sistema,text=f"{COMPANY_NAME}\n{WHATSAPP} | {EMAIL}\n{WEBSITE}",justify="center",text_color="#b0bec5").pack(pady=(0,15))
        ctk.CTkButton(sistema,text="Buscar actualizaciones",command=self.actualizar).pack()

    def guardar(self):
        try:self.servicios.empresa.guardar_empresa(self.ctx,self.campos["ruc"].get(),self.campos["razon"].get(),self.campos["comercial"].get(),self.campos["direccion"].get(),self.campos["telefono"].get(),self.campos["email"].get())
        except Exception as exc:messagebox.showerror("Empresa",str(exc));return
        messagebox.showinfo("Éxito","Datos de empresa actualizados.")

    def respaldar(self):
        carpeta=filedialog.askdirectory(title="Carpeta para el respaldo")
        if not carpeta:return
        try:ruta,_hash=self.servicios.respaldos.crear(self.ctx,carpeta)
        except Exception as exc:messagebox.showerror("Respaldo",str(exc));return
        messagebox.showinfo("Respaldo creado",f"Copia guardada en:\n{ruta}")

    def restaurar(self):
        ruta=filedialog.askopenfilename(title="Seleccionar respaldo",filetypes=[("Respaldo BAP APU","*.db"),("Todos los archivos","*.*")])
        if not ruta:return
        confirmar=messagebox.askyesno("Confirmar restauración","Se reemplazarán los datos actuales. Antes se creará una copia de emergencia.\n\n¿Desea continuar?")
        if not confirmar:return
        try:emergencia=self.servicios.respaldos.restaurar(self.ctx,ruta)
        except Exception as exc:messagebox.showerror("No se pudo restaurar",str(exc));return
        messagebox.showinfo("Restauración completada",f"Los datos fueron restaurados.\nCopia de emergencia:\n{emergencia}\n\nEl sistema se cerrará; vuelva a abrirlo.")
        self.winfo_toplevel().destroy()

    def actualizar(self):
        try:datos=consultar_actualizacion()
        except Exception as exc:messagebox.showerror("Actualización",str(exc));return
        messagebox.showinfo("Actualización",datos.get("mensaje") or ("Nueva versión disponible." if datos.get("hay_actualizacion") else "El sistema está actualizado."))

    def refrescar_licencia(self):
        estado=self.servicios.licencias.verificar_acceso()
        detalle=f"Estado: {estado.modo}\n{estado.mensaje}\nUsuarios permitidos: {estado.max_usuarios}"
        if estado.ruc:detalle+=f"\nRUC: {estado.ruc}\nEmpresa: {estado.empresa}"
        self.lbl_licencia.configure(text=detalle,text_color="#81c784" if estado.modo=="LICENCIA" else "#ffcc80")

    def copiar_codigo(self):
        self.clipboard_clear();self.clipboard_append(codigo_equipo())
        messagebox.showinfo("Código copiado","El código del equipo se copió al portapapeles.")

    def importar_licencia(self):
        ruta=filedialog.askopenfilename(title="Seleccionar licencia",filetypes=[("Licencia APU","*.apulic"),("Todos los archivos","*.*")])
        if not ruta:return
        try:estado=self.servicios.licencias.instalar_licencia(ruta)
        except Exception as exc:messagebox.showerror("Licencia no válida",str(exc));return
        self.refrescar_licencia()
        messagebox.showinfo("Activación correcta",f"Empresa: {estado.empresa}\nRUC: {estado.ruc}\nVence: {estado.vencimiento}\n\nLa licencia ya está activa. Reinicie el programa para actualizar todo el menú.")
