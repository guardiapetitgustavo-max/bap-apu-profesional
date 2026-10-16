"""Contexto de la sesión activa: quién es el usuario y qué puede hacer."""
from dataclasses import dataclass

from bap_apu.errores import PermisoDenegado


@dataclass(frozen=True)
class Contexto:
    usuario_id: int
    usuario: str
    nombre_completo: str
    rol: str
    permisos: frozenset[str]
    empresa_id: int
    token: str

    def puede(self, permiso: str) -> bool:
        return permiso in self.permisos

    def exigir(self, permiso: str) -> None:
        if permiso not in self.permisos:
            raise PermisoDenegado(f"Su rol no permite esta acción ({permiso}).")

    @classmethod
    def desde_sesion(cls, sesion, empresa_id: int) -> "Contexto":
        return cls(
            usuario_id=sesion["id"],
            usuario=sesion["usuario"],
            nombre_completo=sesion["nombre_completo"],
            rol=sesion["rol"],
            permisos=frozenset(sesion["permisos"]),
            empresa_id=empresa_id,
            token=sesion["token"],
        )
