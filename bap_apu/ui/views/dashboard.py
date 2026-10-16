import customtkinter as ctk


class VistaDashboard(ctk.CTkFrame):
    def __init__(self,parent,servicios,ctx):
        super().__init__(parent); datos=servicios.empresa.obtener_dashboard(ctx)
        ctk.CTkLabel(self,text="PANEL EJECUTIVO",font=("Arial",24,"bold")).pack(pady=(20,12))
        tarjetas=ctk.CTkFrame(self,fg_color="transparent"); tarjetas.pack(fill="x",padx=25,pady=10)
        valores=[("Proyectos",datos["proyectos"]),("Clientes",datos["clientes"]),("Recursos",datos["recursos"]),("Partidas",datos["partidas"]),("Costo acumulado",f"S/ {datos['total']:,.2f}")]
        for i,(titulo,valor) in enumerate(valores):
            tarjeta=ctk.CTkFrame(tarjetas,height=105,corner_radius=12); tarjeta.grid(row=0,column=i,padx=7,sticky="nsew"); tarjetas.grid_columnconfigure(i,weight=1)
            ctk.CTkLabel(tarjeta,text=titulo,font=("Arial",12),text_color="#b0bec5").pack(pady=(17,4))
            ctk.CTkLabel(tarjeta,text=str(valor),font=("Arial",20,"bold"),text_color="#64b5f6").pack()
        ctk.CTkLabel(self,text="PROYECTOS RECIENTES",font=("Arial",15,"bold")).pack(anchor="w",padx=30,pady=(25,8))
        lista=ctk.CTkScrollableFrame(self); lista.pack(fill="both",expand=True,padx=25,pady=(0,20))
        for nombre,total in datos["ultimos"]:
            fila=ctk.CTkFrame(lista,height=42); fila.pack(fill="x",pady=2); fila.pack_propagate(False)
            ctk.CTkLabel(fila,text=nombre,anchor="w",font=("Arial",12)).pack(side="left",padx=15)
            ctk.CTkLabel(fila,text=f"S/ {total:,.2f}",font=("Arial",12,"bold"),text_color="#81c784").pack(side="right",padx=15)
