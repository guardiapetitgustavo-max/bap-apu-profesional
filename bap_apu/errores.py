"""Errores propios de BAP APU."""
from pathlib import Path


class ErrorBAP(Exception):
    """Base de los errores de la aplicación."""


class ErrorValidacion(ErrorBAP, ValueError):
    """Datos inválidos; compatible con los `except ValueError` de las vistas."""


class PermisoDenegado(ErrorBAP, PermissionError):
    """El rol del usuario no permite la acción."""


class ErrorMigracion(ErrorBAP):
    def __init__(self, mensaje: str, respaldo: Path | None = None):
        super().__init__(mensaje)
        self.respaldo = respaldo
