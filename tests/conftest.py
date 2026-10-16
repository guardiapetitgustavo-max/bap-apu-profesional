import pytest


@pytest.fixture(scope="session", autouse=True)
def datos_usuario_aislados(tmp_path_factory):
    """Evita que las pruebas escriban en el LOCALAPPDATA real del usuario."""
    carpeta = tmp_path_factory.mktemp("datos_usuario")
    with pytest.MonkeyPatch.context() as mp:
        mp.setenv("LOCALAPPDATA", str(carpeta))
        mp.setenv("XDG_DATA_HOME", str(carpeta))
        yield carpeta


@pytest.fixture
def db(tmp_path):
    """Base nueva, migrada y sembrada, en una carpeta temporal."""
    from bap_apu.arranque import preparar_base
    from bap_apu.data.db import Database

    base = Database(tmp_path / "apu.db")
    preparar_base(base, tmp_path)
    return base


@pytest.fixture
def ctx_admin(db):
    """Contexto del administrador (usuario 1) en su empresa principal."""
    from bap_apu.contexto import Contexto

    with db.lectura() as conn:
        usuario, nombre, rol = conn.execute(
            """SELECT u.usuario, u.nombre_completo, r.nombre
               FROM usuarios u JOIN roles r ON r.id = u.rol_id WHERE u.id = 1"""
        ).fetchone()
        empresa_id = conn.execute(
            """SELECT empresa_id FROM usuario_empresa WHERE usuario_id = 1
               ORDER BY es_principal DESC, empresa_id LIMIT 1"""
        ).fetchone()[0]
        permisos = frozenset(fila[0] for fila in conn.execute(
            """SELECT p.codigo FROM rol_permisos rp
               JOIN permisos p ON p.id = rp.permiso_id
               JOIN roles r ON r.id = rp.rol_id WHERE r.nombre = 'Administrador'"""
        ))
    return Contexto(
        usuario_id=1, usuario=usuario, nombre_completo=nombre, rol=rol,
        permisos=permisos, empresa_id=empresa_id, token="token-de-prueba",
    )
