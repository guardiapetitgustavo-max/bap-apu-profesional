import pytest


@pytest.fixture(scope="session", autouse=True)
def datos_usuario_aislados(tmp_path_factory):
    """Evita que las pruebas escriban en el LOCALAPPDATA real del usuario."""
    carpeta = tmp_path_factory.mktemp("datos_usuario")
    with pytest.MonkeyPatch.context() as mp:
        mp.setenv("LOCALAPPDATA", str(carpeta))
        mp.setenv("XDG_DATA_HOME", str(carpeta))
        yield carpeta
