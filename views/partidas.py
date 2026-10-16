import customtkinter as ctk
from tkinter import messagebox

from database import (
    cargar_partida_en_proyecto,
    obtener_detalle_partida,
    obtener_partidas,
    obtener_proyectos,
)


class VistaPartidas(ctk.CTkFrame):
    """Consulta partidas maestras y permite copiarlas a un proyecto."""

    def __init__(self, parent, can_use=True, empresa_id=None):
        super().__init__(parent)
        self.can_use = can_use
        self.empresa_id = empresa_id
        self.partidas = {}
        self.proyectos = {}

        ctk.CTkLabel(
            self, text="BIBLIOTECA DE PARTIDAS", font=("Arial", 22, "bold")
        ).pack(pady=(15, 8))

        controles = ctk.CTkFrame(self)
        controles.pack(fill="x", padx=20, pady=8)

        self.partida_var = ctk.StringVar(value="Seleccionar partida...")
        self.cb_partida = ctk.CTkOptionMenu(
            controles,
            variable=self.partida_var,
            command=lambda _valor: self.cargar_detalle(),
            width=390,
        )
        self.cb_partida.pack(side="left", padx=10, pady=12)

        self.proyecto_var = ctk.StringVar(value="Seleccionar proyecto...")
        self.cb_proyecto = ctk.CTkOptionMenu(
            controles, variable=self.proyecto_var, width=220
        )
        self.cb_proyecto.pack(side="left", padx=10)

        self.btn_agregar = ctk.CTkButton(
            controles,
            text="Agregar partida al proyecto",
            command=self.agregar_a_proyecto,
            fg_color="#2e7d32",
            hover_color="#1b5e20",
            width=200,
        )
        self.btn_agregar.pack(side="right", padx=10)
        if not self.can_use:
            self.btn_agregar.configure(state="disabled", text="Solo lectura")

        encabezado = ctk.CTkFrame(self, fg_color="#2b2b2b", height=36)
        encabezado.pack(fill="x", padx=20)
        encabezado.pack_propagate(False)
        columnas = [
            ("Recurso", .36), ("Tipo", .15), ("Unidad", .10),
            ("Cuadrilla", .11), ("Cantidad", .10), ("Precio", .09),
            ("Parcial", .09),
        ]
        x = .01
        for texto, ancho in columnas:
            ctk.CTkLabel(
                encabezado, text=texto, font=("Arial", 11, "bold"), anchor="w"
            ).place(relx=x, rely=.2, relwidth=ancho)
            x += ancho

        self.filas = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.filas.pack(fill="both", expand=True, padx=20, pady=(2, 8))
        self.resumen = ctk.CTkLabel(
            self, text="Seleccione una partida", font=("Arial", 13, "bold")
        )
        self.resumen.pack(pady=(0, 12))
        self.inicializar()

    def inicializar(self):
        partidas = obtener_partidas()
        self.partidas = {
            f"{p[1]} [{p[2]}] - S/ {p[3]:,.2f}": p[0] for p in partidas
        }
        self.cb_partida.configure(values=list(self.partidas) or ["Sin partidas"])

        proyectos = obtener_proyectos(self.empresa_id)
        self.proyectos = {p[1]: p[0] for p in proyectos}
        self.cb_proyecto.configure(values=list(self.proyectos) or ["Sin proyectos"])

    def cargar_detalle(self):
        for widget in self.filas.winfo_children():
            widget.destroy()
        partida_id = self.partidas.get(self.partida_var.get())
        if not partida_id:
            return
        detalle = obtener_detalle_partida(partida_id)
        pesos = [.36, .15, .10, .11, .10, .09, .09]
        for indice, item in enumerate(detalle):
            fondo = "#3a3a3a" if indice % 2 == 0 else "#2e2e2e"
            fila = ctk.CTkFrame(self.filas, fg_color=fondo, height=34)
            fila.pack(fill="x", pady=1)
            fila.pack_propagate(False)
            valores = [
                item[1], item[7], item[2], f"{item[3]:.4f}",
                f"{item[4]:.4f}", f"S/ {item[5]:,.2f}", f"S/ {item[6]:,.2f}",
            ]
            x = .01
            for valor, ancho in zip(valores, pesos):
                ctk.CTkLabel(fila, text=valor, font=("Arial", 10), anchor="w").place(
                    relx=x, rely=.15, relwidth=ancho - .01
                )
                x += ancho
        total = sum(item[6] for item in detalle)
        self.resumen.configure(text=f"{len(detalle)} recursos | Total del detalle: S/ {total:,.2f}")

    def agregar_a_proyecto(self):
        partida_id = self.partidas.get(self.partida_var.get())
        proyecto_id = self.proyectos.get(self.proyecto_var.get())
        if not partida_id or not proyecto_id:
            messagebox.showwarning(
                "Selección incompleta", "Seleccione una partida y un proyecto."
            )
            return
        if not messagebox.askyesno(
            "Confirmar", "¿Desea agregar todos los recursos de esta partida al proyecto?"
        ):
            return
        cantidad = cargar_partida_en_proyecto(partida_id, proyecto_id)
        messagebox.showinfo(
            "Partida agregada", f"Se agregaron {cantidad} recursos al APU del proyecto."
        )
