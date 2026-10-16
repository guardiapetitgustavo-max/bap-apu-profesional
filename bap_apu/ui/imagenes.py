import customtkinter as ctk
from PIL import Image

from bap_apu import paths


def cargar_isotipo(tamano):
    imagen = Image.open(paths.recurso("assets", "bap_isotipo.png"))
    return ctk.CTkImage(light_image=imagen, dark_image=imagen, size=(tamano, tamano))
