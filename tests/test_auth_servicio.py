import pytest

from bap_apu.contexto import Contexto
from bap_apu.errores import ErrorValidacion, PermisoDenegado
from bap_apu.security.passwords import hash_password, validar_fortaleza, verify_password
from bap_apu.services.auth import AuthService


@pytest.fixture
def auth(db):
    return AuthService(db, max_usuarios=lambda: 5)


def _ctx_consulta(db, ctx_admin):
    with db.lectura() as conn:
        permisos = frozenset(f[0] for f in conn.execute(
            """SELECT p.codigo FROM rol_permisos rp
               JOIN permisos p ON p.id = rp.permiso_id
               JOIN roles r ON r.id = rp.rol_id WHERE r.nombre = 'Consulta'"""))
    return Contexto(usuario_id=99, usuario="lector", nombre_completo="Lector",
                    rol="Consulta", permisos=permisos,
                    empresa_id=ctx_admin.empresa_id, token="t")


def test_hash_no_guarda_password_y_verifica():
    encoded = hash_password("ClaveSegura1")
    assert "ClaveSegura1" not in encoded
    assert verify_password("ClaveSegura1", encoded)
    assert not verify_password("Incorrecta1", encoded)


def test_login_cambio_obligatorio_y_cierre(auth):
    sesion, error = auth.autenticar("admin", "admin123")
    assert error is None
    assert sesion.debe_cambiar_password
    assert sesion.puede("usuarios.gestionar")
    auth.cambiar_password(sesion.id, "admin123", "AdminNueva1")
    auth.cerrar_sesion(sesion)
    nueva, error = auth.autenticar("admin", "AdminNueva1")
    assert error is None
    assert not nueva.debe_cambiar_password


def test_usuario_consulta_recibe_permisos_limitados(auth, ctx_admin):
    rol_consulta = next(i for i, n in auth.listar_roles(ctx_admin) if n == "Consulta")
    auth.crear_usuario(ctx_admin, "lector", "Usuario Lector", "Lectura123", rol_consulta)
    sesion, error = auth.autenticar("lector", "Lectura123")
    assert error is None
    assert sesion.puede("apu.ver")
    assert not sesion.puede("apu.editar")
    assert not sesion.puede("usuarios.gestionar")


def test_reglas_de_fortaleza():
    assert validar_fortaleza("ClaveSegura1") == []
    assert validar_fortaleza("debil")


def test_crear_usuario_respeta_limite(db, ctx_admin):
    auth = AuthService(db, max_usuarios=lambda: 1)
    with pytest.raises(ErrorValidacion, match="como máximo 1"):
        auth.crear_usuario(ctx_admin, "otro", "Otro Usuario", "Clave12345", 1)


def test_consulta_no_puede_listar_usuarios(auth, db, ctx_admin):
    with pytest.raises(PermisoDenegado):
        auth.listar_usuarios(_ctx_consulta(db, ctx_admin))


def test_bloqueo_tras_5_fallos(auth):
    for _ in range(5):
        sesion, error = auth.autenticar("admin", "mala")
        assert sesion is None and error == "Usuario o contraseña incorrectos."
    sesion, error = auth.autenticar("admin", "admin123")
    assert sesion is None
    assert error == "Cuenta bloqueada temporalmente. Intente nuevamente más tarde."


def test_fallo_persiste_auditoria(auth, db, ctx_admin):
    auth.autenticar("admin", "mala")
    from bap_apu.data.repos import auditoria
    with db.lectura() as conn:
        filas = auditoria.listar(conn, 10)
    assert any(f[2] == "LOGIN_FALLIDO" for f in filas)


def test_no_puede_desactivarse_a_si_mismo(auth, ctx_admin):
    with pytest.raises(ErrorValidacion, match="propia cuenta"):
        auth.cambiar_estado_usuario(ctx_admin, ctx_admin.usuario_id, False)
