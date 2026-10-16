import customtkinter as ctk
from tkinter import filedialog,messagebox
from services.offline_license import codigo_equipo,instalar_licencia
from brand import APP_NAME, COMPANY_NAME, WHATSAPP, EMAIL, COLOR_TEAL


class VentanaActivacion:
    def __init__(self,estado):
        self.activada=False;self.root=ctk.CTk();self.root.title(f"Activar {APP_NAME}");self.root.geometry("640x530");self.root.resizable(False,False)
        ctk.CTkLabel(self.root,text=APP_NAME.upper(),font=("Arial",22,"bold"),text_color=COLOR_TEAL).pack(pady=(28,3))
        ctk.CTkLabel(self.root,text="ACTIVACIÓN OFFLINE",font=("Arial",16,"bold")).pack(pady=(0,10))
        ctk.CTkLabel(self.root,text=estado.mensaje,font=("Arial",14,"bold"),text_color="#ef9a9a").pack(pady=6)
        ctk.CTkLabel(self.root,text="Envíe su RUC y este código de equipo al vendedor:").pack(pady=(18,5))
        self.codigo=ctk.CTkEntry(self.root,width=390,justify="center",font=("Consolas",15,"bold"));self.codigo.insert(0,codigo_equipo());self.codigo.configure(state="readonly");self.codigo.pack(pady=6)
        ctk.CTkButton(self.root,text="Copiar código",command=self.copiar,width=150).pack(pady=5)
        ctk.CTkLabel(self.root,text="Realice el pago por Yape, Plin o transferencia.\nLuego importe el archivo .apulic que recibirá.",justify="center").pack(pady=14)
        ctk.CTkLabel(self.root,text=f"Soporte BAP: {WHATSAPP}\n{EMAIL}",justify="center",text_color="#b0bec5").pack(pady=5)
        ctk.CTkButton(self.root,text="Importar licencia .apulic",command=self.importar,fg_color="#2e7d32",hover_color="#1b5e20",width=230,height=40).pack(pady=6)
        ctk.CTkButton(self.root,text="Cerrar",command=self.root.destroy,fg_color="#616161",width=120).pack(pady=10)
    def run(self):self.root.mainloop();return self.activada
    def copiar(self):self.root.clipboard_clear();self.root.clipboard_append(codigo_equipo());messagebox.showinfo("Copiado","Código copiado.")
    def importar(self):
        ruta=filedialog.askopenfilename(filetypes=[("Licencia APU","*.apulic"),("Todos","*.*")])
        if not ruta:return
        try:estado=instalar_licencia(ruta)
        except Exception as exc:messagebox.showerror("Licencia",str(exc));return
        self.activada=True;messagebox.showinfo("Activación correcta",f"Empresa: {estado.empresa}\nRUC: {estado.ruc}\nVence: {estado.vencimiento}");self.root.destroy()
