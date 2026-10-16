import customtkinter as ctk
from tkinter import messagebox
from services.business_service import crear_cliente,crear_proveedor,listar_clientes,listar_proveedores


class VistaTerceros(ctk.CTkFrame):
    def __init__(self,parent,sesion,empresa_id,can_edit=True):
        super().__init__(parent); self.sesion=sesion; self.empresa_id=empresa_id; self.can_edit=can_edit
        ctk.CTkLabel(self,text="CLIENTES Y PROVEEDORES",font=("Arial",22,"bold")).pack(pady=15)
        tabs=ctk.CTkTabview(self); tabs.pack(fill="both",expand=True,padx=20,pady=(0,20))
        self._crear_tab_clientes(tabs.add("Clientes")); self._crear_tab_proveedores(tabs.add("Proveedores"))

    def _entrada(self,parent,placeholder):
        e=ctk.CTkEntry(parent,placeholder_text=placeholder,width=200); e.pack(side="left",padx=4,pady=10); return e

    def _crear_tab_clientes(self,tab):
        form=ctk.CTkFrame(tab); form.pack(fill="x",pady=8)
        self.c_doc=self._entrada(form,"RUC/DNI"); self.c_nombre=self._entrada(form,"Nombre o razón social"); self.c_tel=self._entrada(form,"Teléfono"); self.c_email=self._entrada(form,"Email")
        b=ctk.CTkButton(form,text="Agregar",width=100,command=self.guardar_cliente); b.pack(side="right",padx=8)
        if not self.can_edit:b.configure(state="disabled")
        self.lista_clientes=ctk.CTkScrollableFrame(tab); self.lista_clientes.pack(fill="both",expand=True); self.cargar_clientes()

    def _crear_tab_proveedores(self,tab):
        form=ctk.CTkFrame(tab); form.pack(fill="x",pady=8)
        self.p_ruc=self._entrada(form,"RUC"); self.p_nombre=self._entrada(form,"Proveedor"); self.p_contacto=self._entrada(form,"Contacto"); self.p_tel=self._entrada(form,"Teléfono")
        b=ctk.CTkButton(form,text="Agregar",width=100,command=self.guardar_proveedor); b.pack(side="right",padx=8)
        if not self.can_edit:b.configure(state="disabled")
        self.lista_proveedores=ctk.CTkScrollableFrame(tab); self.lista_proveedores.pack(fill="both",expand=True); self.cargar_proveedores()

    def _fila(self,parent,valores):
        fila=ctk.CTkFrame(parent,height=38); fila.pack(fill="x",pady=2); fila.pack_propagate(False)
        for i,valor in enumerate(valores): ctk.CTkLabel(fila,text=str(valor or ""),anchor="w",width=190).pack(side="left",padx=8)

    def guardar_cliente(self):
        try: crear_cliente(self.sesion.id,self.empresa_id,"RUC",self.c_doc.get(),self.c_nombre.get(),"",self.c_tel.get(),self.c_email.get())
        except Exception as exc: messagebox.showerror("Cliente",str(exc)); return
        for e in (self.c_doc,self.c_nombre,self.c_tel,self.c_email):e.delete(0,"end")
        self.cargar_clientes()

    def guardar_proveedor(self):
        try: crear_proveedor(self.sesion.id,self.empresa_id,self.p_ruc.get(),self.p_nombre.get(),self.p_contacto.get(),self.p_tel.get(),"")
        except Exception as exc: messagebox.showerror("Proveedor",str(exc)); return
        for e in (self.p_ruc,self.p_nombre,self.p_contacto,self.p_tel):e.delete(0,"end")
        self.cargar_proveedores()

    def cargar_clientes(self):
        for w in self.lista_clientes.winfo_children():w.destroy()
        for c in listar_clientes(self.empresa_id):self._fila(self.lista_clientes,(c[2],c[3],c[5],c[6]))

    def cargar_proveedores(self):
        for w in self.lista_proveedores.winfo_children():w.destroy()
        for p in listar_proveedores(self.empresa_id):self._fila(self.lista_proveedores,(p[1],p[2],p[3],p[4]))
