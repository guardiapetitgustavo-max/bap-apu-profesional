"""Acceso a SQLite con conexiones que siempre se cierran."""
import sqlite3
from contextlib import contextmanager
from pathlib import Path


class ConexionCerrable(sqlite3.Connection):
    """Conexión cuyo `with` confirma o revierte y además la cierra."""

    def __exit__(self, exc_type, exc_value, traceback):
        try:
            return super().__exit__(exc_type, exc_value, traceback)
        finally:
            self.close()


class Database:
    def __init__(self, ruta):
        self.ruta = Path(ruta)

    def conectar(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.ruta, factory=ConexionCerrable)
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA busy_timeout = 5000")
        return conn

    @contextmanager
    def transaccion(self):
        conn = self.conectar()
        try:
            yield conn
            conn.commit()
        except BaseException:
            conn.rollback()
            raise
        finally:
            conn.close()

    @contextmanager
    def lectura(self):
        conn = self.conectar()
        try:
            yield conn
        finally:
            conn.close()
