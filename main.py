from tkinter import messagebox

from bap_apu import paths
from bap_apu.arranque import preparar_base
from bap_apu.contexto import Contexto
from bap_apu.data.db import Database
from bap_apu.errores import ErrorMigracion
from bap_apu.servicios import crear_servicios
from bap_apu.ui.app import AppAPU
from bap_apu.ui.login import LoginWindow
from bap_apu.ui.views.activacion import VentanaActivacion


def main() -> int:
    db = Database(paths.ruta_base_datos())
    carpeta = paths.carpeta_datos()
    try:
        preparar_base(db, carpeta)
    except ErrorMigracion as e:
        messagebox.showerror("No se pudo actualizar la base de datos", str(e))
        return 1
    servicios = crear_servicios(db, carpeta)
    estado_actual = servicios.licencias.verificar_acceso()
    if not estado_actual.permitido:
        if not VentanaActivacion(servicios, estado_actual).run():
            return 0
        estado_actual = servicios.licencias.verificar_acceso()
        if not estado_actual.permitido:
            return 1
    while True:
        sesion_actual = LoginWindow(servicios).run()
        if not sesion_actual:
            break
        empresa = servicios.empresa.empresa_principal(sesion_actual.id)
        if not empresa:
            messagebox.showerror("Empresa", "El usuario no tiene una empresa asignada.")
            servicios.auth.cerrar_sesion(sesion_actual)
            break
        ctx = Contexto.desde_sesion(sesion_actual, empresa[0])
        app = AppAPU(servicios, sesion_actual, ctx, estado_actual)
        app.mainloop()
        if not app.solicito_cerrar_sesion:
            servicios.auth.cerrar_sesion(sesion_actual)
            break
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
