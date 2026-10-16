import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1] / "bap_apu"


def _fuentes(subcarpeta, recursivo=True):
    patron = "**/*.py" if recursivo else "*.py"
    return sorted((RAIZ / subcarpeta).glob(patron))


def test_ui_sin_sql():
    prohibidos = ("import sqlite3", "bap_apu.data", "SELECT ", "INSERT ", "UPDATE ", "DELETE ")
    for archivo in _fuentes("ui"):
        texto = archivo.read_text(encoding="utf-8")
        for texto_prohibido in prohibidos:
            assert texto_prohibido not in texto, f"{archivo.name} contiene {texto_prohibido!r}"


def test_core_puro():
    patron = re.compile(r"^\s*(import|from)\s+(sqlite3|tkinter|customtkinter|bap_apu)\b", re.M)
    for archivo in _fuentes("core", recursivo=False):
        assert not patron.search(archivo.read_text(encoding="utf-8")), archivo.name


def test_servicios_sin_tk():
    patron = re.compile(r"^\s*(import|from)\s+(tkinter|customtkinter)\b", re.M)
    for archivo in _fuentes("services", recursivo=False):
        assert not patron.search(archivo.read_text(encoding="utf-8")), archivo.name
