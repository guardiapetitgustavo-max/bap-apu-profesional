import customtkinter as ctk
from tkinter import filedialog,messagebox


class VistaReportes(ctk.CTkFrame):
    def __init__(self,parent,servicios,ctx):
        super().__init__(parent); self.servicios=servicios; self.ctx=ctx
        can_export=ctx.puede("reportes.exportar"); can_audit=ctx.puede("auditoria.ver")
        ctk.CTkLabel(self,text="REPORTES Y AUDITORÍA",font=("Arial",22,"bold")).pack(pady=15)
        barra=ctk.CTkFrame(self); barra.pack(fill="x",padx=20,pady=5)
        boton=ctk.CTkButton(barra,text="Exportar resumen a Excel",command=self.exportar); boton.pack(side="left",padx=10,pady=10)
        if not can_export:boton.configure(state="disabled")
        tabs=ctk.CTkTabview(self); tabs.pack(fill="both",expand=True,padx=20,pady=10)
        resumen=tabs.add("Información"); ctk.CTkLabel(resumen,text="El Excel incluye proyectos, costos APU, clientes, recursos y partidas.",font=("Arial",14)).pack(pady=35)
        audit=tabs.add("Auditoría"); lista=ctk.CTkScrollableFrame(audit); lista.pack(fill="both",expand=True)
        if can_audit:
            for fecha,usuario,accion,entidad,detalle in servicios.empresa.listar_auditoria(ctx):
                fila=ctk.CTkFrame(lista,height=36); fila.pack(fill="x",pady=1); fila.pack_propagate(False)
                ctk.CTkLabel(fila,text=f"{fecha} | {usuario} | {accion} | {entidad} | {detalle}",anchor="w",font=("Arial",10)).pack(fill="x",padx=8,pady=7)
        else: ctk.CTkLabel(lista,text="Su rol no permite consultar la auditoría.").pack(pady=30)

    def exportar(self):
        ruta=filedialog.asksaveasfilename(defaultextension=".xlsx",filetypes=[("Excel","*.xlsx")],initialfile="Reporte_APU.xlsx")
        if not ruta:return
        try:self.servicios.reportes.exportar_excel(self.ctx,ruta)
        except Exception as exc:messagebox.showerror("Reporte",str(exc));return
        messagebox.showinfo("Reporte generado",f"Archivo guardado en:\n{ruta}")
