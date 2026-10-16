# Fase 1 — Cimientos (BAP APU Profesional 1.5.0) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reorganizar BAP APU 1.4.0 en el paquete `bap_apu/` por capas, con migraciones versionadas y permisos en servicios, sin cambiar lo que ve el usuario.

**Architecture:** El código nuevo crece junto al viejo. Cada tarea traslada un área (datos, auth, licencias, negocio, APU, importación, respaldos, reportes) a `bap_apu/` y porta sus pruebas. La tarea 11 cambia la interfaz al código nuevo y la 12 borra el viejo. Los repositorios son funciones que reciben `conn`. Los servicios son clases que reciben `Database` y abren la transacción, de modo que operación y auditoría quedan en una sola transacción.

**Tech Stack:** Python 3.12, customtkinter 5, SQLite (`sqlite3`), ReportLab 4, openpyxl 3, cryptography, pytest 9, PyInstaller, Inno Setup.

**Spec:** `docs/superpowers/specs/2026-10-16-reestructuracion-bap-apu-design.md` (secciones 4, 5, 8 y 9).

## Global Constraints

- Versión de la app: `1.5.0`, en `bap_apu/brand.py` y en `installer/BAP_APU_Profesional.iss`.
- Dependencias de ejecución sin cambios (`requirements.txt`). Dependencias de desarrollo en `requirements-dev.txt`: `-r requirements.txt` + `pytest>=8,<10`.
- Carpeta de datos: `%LOCALAPPDATA%\BAP_APU_Profesional\`. Archivos `apu.db`, `licencia.apulic` y `.trial.dat` con los mismos nombres.
- `PUBLIC_KEY_DER_B64 = "MCowBQYDK2VwAyEAW4ztBQMWmPl7KlLS9nicavQ4joZghmFe8Gb1SQZGkS4="`, `MARKER_SECRET`, `TRIAL_DAYS = 15` y `MAX_DEVICES = 5`, copiados exactos.
- Los repositorios devuelven **las mismas tuplas, en el mismo orden de columnas**, que las funciones legadas que reemplazan (las vistas indexan por posición).
- Textos visibles en español; los mensajes existentes se copian literales.
- `ErrorValidacion` hereda de `ValueError` y `PermisoDenegado` de `PermissionError`, para que los `except ValueError` de las vistas sigan funcionando.
- Commits en español, **sin** líneas `Co-Authored-By` ni "Generated with Claude Code" (CLAUDE.md del proyecto).
- Pruebas: `.venv/Scripts/python -m pytest -q` desde `bap-apu/`. Ninguna prueba puede escribir en el `LOCALAPPDATA` real.
- `ui/` nunca importa `sqlite3` ni `bap_apu.data`; `core/` no importa nada del proyecto, de tkinter ni de sqlite3.

## Review Focus

1. **Base creada por una versión más nueva** (`user_version` > `VERSION_ESQUEMA`): debe negarse a abrirla con un mensaje claro, sin tocarla. Prueba en la tarea 3.
2. **No se puede escribir el respaldo previo** (carpeta inválida o disco lleno): no debe migrar sin respaldo; la base queda en su versión original. Prueba en la tarea 3.
3. **Restaurar un respaldo 1.4.0 con la 1.5.0 abierta**: la base restaurada se migra al instante. Si la migración falla, vuelve la copia de emergencia. Además, la restauración funciona en Windows después de varias operaciones (sin conexiones abiertas que bloqueen el archivo). Prueba en la tarea 9.
4. **IDs de otra empresa** (proyecto, ítem de APU): leer, borrar o cargar partidas con IDs ajenos lanza `ErrorValidacion` y no cambia nada. Prueba en la tarea 7.
5. **Licencias y marcador de prueba fuera de la carpeta indicada**: `LicenciaService` escribe solo en la `carpeta` que recibe. Prueba en la tarea 5.

---

### Task 1: Arnés de pruebas y cierre de conexiones (base en verde)

Hoy fallan 10 de 19 pruebas en Windows porque `with conectar()` y `with sqlite3.connect()` no cierran la conexión, y el archivo queda bloqueado.

**Files:**
- Create: `requirements-dev.txt`, `pytest.ini`, `tests/conftest.py`, `tests/test_conexiones.py`, `tests/fixtures/crear_base_1_4_0.py`, `tests/fixtures/base_1_4_0_con_datos.db`
- Modify: `database.py` (`conectar`, `_es_base_apu_valida`), `services/business_service.py` (`restaurar_respaldo`), `tests/test_backup_restore.py`, `tests/test_instalacion_db.py`

**Interfaces:**
- Produces: fixture de sesión autouse en `tests/conftest.py` que apunta `LOCALAPPDATA` y `XDG_DATA_HOME` a un directorio temporal; `tests/fixtures/base_1_4_0_con_datos.db` (base 1.4.0 real con datos, `user_version = 0`).

- [ ] **Step 1: Configurar el arnés.** `pytest.ini` con `[pytest]`, `testpaths = tests` y `pythonpath = .`. Crear `requirements-dev.txt` según Global Constraints. En `conftest.py`, una fixture `scope="session", autouse=True` que use `pytest.MonkeyPatch.context()` para fijar `LOCALAPPDATA` y `XDG_DATA_HOME` en `tmp_path_factory.mktemp("datos_usuario")`.

- [ ] **Step 2: Escribir la prueba que falla**

```python
# tests/test_conexiones.py
import sqlite3, pytest, database

def test_with_conectar_cierra_la_conexion(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", str(tmp_path / "c.db"))
    with database.conectar() as conn:
        conn.execute("SELECT 1")
    with pytest.raises(sqlite3.ProgrammingError):
        conn.execute("SELECT 1")
```

- [ ] **Step 3: Ejecutar:** `.venv/Scripts/python -m pytest tests/test_conexiones.py -q`. Expected: FAIL (no se lanza `ProgrammingError`).

- [ ] **Step 4: Implementar.** En `database.py`, definir `class ConexionCerrable(sqlite3.Connection)` cuyo `__exit__` llama a `super().__exit__` (commit o rollback), luego a `self.close()` y devuelve el resultado. `conectar()` usa `sqlite3.connect(DB_PATH, factory=ConexionCerrable)`. En `_es_base_apu_valida` y `restaurar_respaldo`, envolver `sqlite3.connect(...)` con `contextlib.closing`. En las pruebas `test_backup_restore.py` y `test_instalacion_db.py`, envolver con `closing` cada `sqlite3.connect` usado en `with`. En `test_backup_restore.py`, copiar `data/apu_seed.db` en lugar de `apu.db` (que ya no está versionado).

- [ ] **Step 5: Generar la fixture 1.4.0.** Escribir `tests/fixtures/crear_base_1_4_0.py` (`python tests/fixtures/crear_base_1_4_0.py <salida.db>`). El script usa el `database.py` legado de la raíz con `DB_PATH` apuntando a la salida, llama a `crear_tablas()` e inserta: un usuario extra con rol Consulta; dos proyectos de la empresa 1 ("Vivienda Los Pinos" y "Losa deportiva"); en el primero, filas de `detalle_apu` con tipos `"Mano de Obra"`, `"mano de obra "`, `"Materiales"`, `"Material"`, `"Equipos"` y `"Herramientas"` (tipo no reconocido, que suma al total pero no a los subtotales); en el segundo, 3 filas; además un cliente, un proveedor, una fila en `proveedor_precios` y otra en `historial_precios`. El docstring indica que se generó con el commit `71fd64f` y que para regenerarla hay que usar un worktree de ese commit. Ejecutarlo y guardar `tests/fixtures/base_1_4_0_con_datos.db`.

- [ ] **Step 6: Ejecutar todo:** `.venv/Scripts/python -m pytest -q`. Expected: `20 passed`.

- [ ] **Step 7: Commit**

```bash
git add -A && git commit -m "Pruebas: arnés aislado, cierre de conexiones y base 1.4.0 de referencia"
```

---

### Task 2: Paquete base — marca, rutas, errores, contexto y `Database`

**Files:**
- Create: `bap_apu/__init__.py`, `bap_apu/brand.py`, `bap_apu/paths.py`, `bap_apu/errores.py`, `bap_apu/contexto.py`, `bap_apu/data/__init__.py`, `bap_apu/data/db.py`, `bap_apu/data/instalacion.py`, `bap_apu/services/__init__.py`, `bap_apu/services/actualizaciones.py`, `bap_apu/security/__init__.py`, `bap_apu/security/passwords.py`
- Test: `tests/test_base_paquete.py`

**Interfaces:**
- Produces:
  - `bap_apu.brand`: las constantes de `brand.py` más `UPDATE_MANIFEST_URL = ""`, con `APP_VERSION = "1.5.0"`.
  - `bap_apu.paths`: `raiz_recursos() -> Path` (`sys._MEIPASS` o la raíz del repo, `Path(__file__).resolve().parents[1]`); `recurso(*partes: str) -> Path`; `carpeta_datos() -> Path` (misma lógica que `offline_license.carpeta_datos`, crea la carpeta); `ruta_base_datos() -> Path` (misma lógica que `database._resolver_db_path`).
  - `bap_apu.errores`: `ErrorBAP(Exception)`; `ErrorValidacion(ErrorBAP, ValueError)`; `PermisoDenegado(ErrorBAP, PermissionError)`; `ErrorMigracion(ErrorBAP)` con atributo `respaldo: Path | None` (`__init__(self, mensaje: str, respaldo: Path | None = None)`).
  - `bap_apu.contexto.Contexto`, dataclass congelada: `usuario_id: int`, `usuario: str`, `nombre_completo: str`, `rol: str`, `permisos: frozenset[str]`, `empresa_id: int`, `token: str`. Métodos: `puede(permiso) -> bool`; `exigir(permiso) -> None`, que lanza `PermisoDenegado(f"Su rol no permite esta acción ({permiso}).")`; y `@classmethod desde_sesion(sesion, empresa_id) -> Contexto` (lee `id`, `usuario`, `nombre_completo`, `rol`, `permisos` y `token`).
  - `bap_apu.data.db.Database(ruta)`: `ruta: Path`; `conectar() -> sqlite3.Connection` (con `ConexionCerrable`, `PRAGMA foreign_keys = ON` y `busy_timeout = 5000`); `transaccion()`, un context manager que hace commit, o rollback ante error, y siempre cierra; `lectura()`, un context manager sin commit que siempre cierra.
  - `bap_apu.data.instalacion`: `TABLAS_MINIMAS`, `es_base_apu_valida(ruta) -> bool` e `instalar_base_inicial(destino, plantilla, legado=None) -> Path`, con la lógica legada y conexiones cerradas.
  - `bap_apu.security.passwords`: copia de `security/passwords.py`.
  - `bap_apu.services.actualizaciones.consultar_actualizacion(url=None) -> dict` y `_version`: copia de `services/update_service.py` que importa de `bap_apu.brand`.

- [ ] **Step 1: Escribir las pruebas que fallan** en `tests/test_base_paquete.py`:
  - `test_version_1_5_0`: `bap_apu.brand.APP_VERSION == "1.5.0"` y `WHATSAPP == "+51 904 170 143"`.
  - `test_transaccion_hace_rollback_y_cierra`: crea una tabla `t(x)`; dentro de `db.transaccion()` inserta 1 y lanza `RuntimeError`; después `SELECT COUNT(*) FROM t` == 0, y la conexión capturada lanza `sqlite3.ProgrammingError` al usarla.
  - `test_lectura_cierra`: tras `with db.lectura() as c`, `c.execute` lanza `ProgrammingError`.
  - `test_foreign_keys_activas`: `db.conectar().execute("PRAGMA foreign_keys").fetchone()[0] == 1`.
  - `test_contexto_exigir`: un `Contexto` con permisos `{"apu.ver"}` pasa `exigir("apu.ver")` y lanza `PermisoDenegado` con `exigir("apu.editar")`; `isinstance(err, PermissionError)` es verdadero.
  - `test_error_validacion_es_value_error`.
  - `test_instalacion_no_sobrescribe`: portar los dos casos de `tests/test_instalacion_db.py` a `bap_apu.data.instalacion`.
  - `test_recurso_apunta_a_assets`: `paths.recurso("assets", "bap_isotipo.png").is_file()`.
  - `test_version_compara`: `_version("1.10.0") > _version("1.9.9")` y `_version("x") == (0,)`.
- [ ] **Step 2: Ejecutar:** `.venv/Scripts/python -m pytest tests/test_base_paquete.py -q`. Expected: FAIL con `ModuleNotFoundError: bap_apu`.
- [ ] **Step 3: Implementar** los módulos de la lista **Produces**.
- [ ] **Step 4: Ejecutar todo:** `.venv/Scripts/python -m pytest -q`. Expected: todo en verde.
- [ ] **Step 5: Commit:** `git add -A && git commit -m "Paquete bap_apu: marca 1.5.0, rutas, errores, contexto y Database"`

---

### Task 3: Migraciones versionadas y semillas

**Files:**
- Create: `bap_apu/data/migraciones/__init__.py`, `bap_apu/data/migraciones/runner.py`, `bap_apu/data/migraciones/m0001_esquema_1_4_0.py`, `bap_apu/data/semillas.py`, `bap_apu/arranque.py`
- Modify: `tests/conftest.py` (fixtures `db` y `ctx_admin`)
- Test: `tests/test_migraciones.py`

**Interfaces:**
- Consumes: `Database`, `ErrorMigracion` y `hash_password` (tarea 2).
- Produces:
  - `m0001_esquema_1_4_0.aplicar(conn) -> None`: copia **literal** de las sentencias `CREATE TABLE`, de las llamadas a `_agregar_columna_si_falta` y de los índices de `database.crear_tablas()` (commit `71fd64f`), más `CREATE TABLE IF NOT EXISTS control_prueba` (de `offline_license.inicializar_control_prueba`). No hace commit.
  - `semillas.sembrar(conn) -> None`: copia literal de `_sembrar_seguridad` y `_sembrar_empresa_y_planes`. Es idempotente y se ejecuta en cada arranque.
  - `runner.Migracion(version: int, nombre: str, aplicar: Callable)`; `MIGRACIONES = (Migracion(1, "esquema_1_4_0", m0001.aplicar),)`; `VERSION_ESQUEMA = MIGRACIONES[-1].version`.
  - `runner.ResultadoMigracion(version_inicial: int, version_final: int, respaldo: Path | None)`.
  - `runner.respaldar_sqlite(origen: Path, destino: Path) -> Path`: usa `sqlite3.Connection.backup`, verifica `PRAGMA integrity_check == "ok"` en el destino y, si falla, lo borra y lanza `ErrorMigracion`. Crea la carpeta padre.
  - `runner.migrar(db, carpeta_respaldos: Path, migraciones=MIGRACIONES) -> ResultadoMigracion`.
  - `arranque.preparar_base(db, carpeta_datos: Path) -> ResultadoMigracion`: llama a `migrar(db, carpeta_datos / "respaldos")` y luego a `sembrar` dentro de `db.transaccion()`.
  - Fixtures de conftest: `db(tmp_path) -> Database`, ya preparada; `ctx_admin(db) -> Contexto` (usuario 1, empresa principal y todos los permisos del rol Administrador leídos de la base).

Algoritmo de `migrar` (no lo determinan las pruebas):

```
v = PRAGMA user_version; objetivo = migraciones[-1].version
si v > objetivo: ErrorMigracion("La base de datos fue creada con una versión más reciente de BAP APU Profesional. Actualice el programa.")
si v == objetivo: devolver (v, v, None)
respaldo = None
si la base tiene al menos una tabla:
    respaldo = respaldar_sqlite(db.ruta, carpeta_respaldos / f"pre_migracion_v{v}_{AAAAMMDD_HHMMSS}.db")   # si falla: no migrar
conn = sqlite3.connect(db.ruta, isolation_level=None)
por cada migración con version > v, en orden:
    BEGIN IMMEDIATE; m.aplicar(conn); PRAGMA user_version = m.version; COMMIT
    ante excepción: ROLLBACK; ErrorMigracion(
        f"No se pudo actualizar la base de datos (paso {m.version}: {m.nombre}): {exc}. "
        f"Sus datos están respaldados en: {respaldo}", respaldo)
cerrar conn siempre
```

- [ ] **Step 1: Escribir las pruebas que fallan** en `tests/test_migraciones.py`:
  - `test_base_nueva_queda_en_v1_sin_respaldo`: base vacía; resultado `(0, 1, None)` y tablas `empresas`, `usuarios`, `detalle_apu` y `control_prueba` presentes.
  - `test_base_1_4_0_migra_con_respaldo_y_conserva_datos`: copiar la fixture con datos; tras `preparar_base`, `user_version == 1`, el respaldo existe y `COUNT(*)` de `proyectos`, `detalle_apu`, `recursos`, `usuarios`, `proveedor_precios` e `historial_precios` es igual al de antes.
  - `test_esquema_equivalente_a_1_4_0`: para cada tabla de la fixture 1.4.0, el conjunto de nombres de columna (`PRAGMA table_info`) es igual al de una base nueva preparada con `preparar_base` (salvo `control_prueba`, que la fixture no tiene).
  - `test_segunda_ejecucion_no_respalda`: un segundo `migrar` devuelve `respaldo is None`.
  - `test_semillas_idempotentes`: dos llamadas a `preparar_base` dejan 1 usuario `admin` y la misma cantidad de `rol_permisos`.
  - `test_falla_hace_rollback` (Review Focus 1): una `migraciones` extra con `Migracion(2, "rota", f)`, donde `f` crea la tabla `x` y luego lanza; se espera `ErrorMigracion` con `respaldo` existente, `user_version == 1` y sin tabla `x`.
  - `test_rechaza_base_mas_nueva` (Review Focus 1): `PRAGMA user_version = 99`; se espera `ErrorMigracion` con "versión más reciente" y el archivo sin cambios (mismo SHA-256).
  - `test_sin_respaldo_no_migra` (Review Focus 2): fixture 1.4.0 con `carpeta_respaldos` igual a la ruta de un **archivo** existente; se espera `ErrorMigracion` y `user_version == 0`.
- [ ] **Step 2: Ejecutar:** `.venv/Scripts/python -m pytest tests/test_migraciones.py -q`. Expected: FAIL (`ModuleNotFoundError`).
- [ ] **Step 3: Implementar** según la lista **Produces** y el algoritmo.
- [ ] **Step 4: Ejecutar todo:** `.venv/Scripts/python -m pytest -q`. Expected: todo en verde.
- [ ] **Step 5: Commit:** `git add -A && git commit -m "Migraciones versionadas con respaldo previo y semillas idempotentes"`

---

### Task 4: Autenticación y usuarios

**Files:**
- Create: `bap_apu/data/repos/__init__.py`, `bap_apu/data/repos/usuarios.py`, `bap_apu/data/repos/auditoria.py`, `bap_apu/services/auth.py`
- Test: `tests/test_auth_servicio.py` (porta y luego reemplaza `tests/test_auth.py`; borrar el viejo en esta tarea)

**Interfaces:**
- Consumes: `Database`, `Contexto`, `ErrorValidacion`, fixtures `db` y `ctx_admin`.
- Produces:
  - `repos/auditoria.registrar(conn, usuario_id, accion, entidad, detalle) -> None` y `repos/auditoria.listar(conn, limite) -> list[tuple]` (SQL de `listar_auditoria`).
  - `repos/usuarios`: `buscar_para_login(conn, usuario)`, `registrar_fallo(conn, usuario_id, intentos, bloqueo)`, `registrar_acceso(conn, usuario_id, token)`, `permisos_de(conn, usuario_id) -> frozenset[str]`, `hash_de(conn, usuario_id) -> str | None`, `actualizar_password(conn, usuario_id, hash)`, `cerrar_sesion(conn, token)`, `listar_roles(conn)`, `listar(conn)`, `contar_activos(conn) -> int`, `insertar(conn, usuario, nombre, hash, rol_id) -> int`, `cambiar_estado(conn, usuario_id, activo)`. El SQL y las tuplas salen de `services/auth_service.py`.
  - `services/auth.UsuarioSesion`: igual a la legada.
  - `services/auth.AuthService(db, max_usuarios: Callable[[], int])` con `autenticar(usuario, password) -> tuple[UsuarioSesion | None, str | None]`, `cambiar_password(usuario_id, actual, nueva)`, `cerrar_sesion(sesion)`, `listar_roles(ctx)`, `listar_usuarios(ctx)`, `crear_usuario(ctx, usuario, nombre, password, rol_id)` y `cambiar_estado_usuario(ctx, usuario_id, activo)`. Los cuatro métodos con `ctx` exigen `usuarios.gestionar`. Mensajes literales del legado; los errores de validación se lanzan como `ErrorValidacion`.

- [ ] **Step 1: Escribir las pruebas que fallan:** portar los 4 casos de `test_auth.py` a `AuthService` (con `max_usuarios=lambda: 5`) y agregar:
  - `test_crear_usuario_respeta_limite`: con `max_usuarios=lambda: 1`, `crear_usuario` lanza `ErrorValidacion` con "como máximo 1".
  - `test_consulta_no_puede_listar_usuarios`: un `Contexto` con permisos de Consulta lanza `PermisoDenegado`.
  - `test_bloqueo_tras_5_fallos`: 5 intentos fallidos; el sexto, con la contraseña correcta, devuelve "Cuenta bloqueada temporalmente. Intente nuevamente más tarde."
- [ ] **Step 2: Ejecutar:** `.venv/Scripts/python -m pytest tests/test_auth_servicio.py -q`. Expected: FAIL (`ModuleNotFoundError`).
- [ ] **Step 3: Implementar** los repos y `AuthService`.
- [ ] **Step 4: Ejecutar todo:** `.venv/Scripts/python -m pytest -q`. Expected: todo en verde.
- [ ] **Step 5: Commit:** `git add -A && git commit -m "Servicio de autenticación y usuarios con permisos verificados"`

---

### Task 5: Licencias offline

**Files:**
- Create: `bap_apu/licensing/__init__.py`, `bap_apu/licensing/offline_license.py`, `bap_apu/services/licencias.py`, `bap_apu/data/repos/empresas.py` (solo `actualizar_por_licencia`; la tarea 6 lo amplía)
- Test: `tests/test_licencias.py` (reemplaza `tests/test_licencia_bap.py`)

**Interfaces:**
- Consumes: `Database`, fixture `db`.
- Produces:
  - `licensing/offline_license`: las constantes de Global Constraints, `EstadoLicencia` (igual a la legada), `codigo_equipo() -> str`, `validar_payload(documento) -> EstadoLicencia` (antes `_validar_payload`; lee `PUBLIC_KEY_DER_B64` y `codigo_equipo` del módulo en cada llamada, para poder parcharlos), `leer_marcador(carpeta) -> dict | None` y `guardar_marcador(carpeta, inicio, ultimo) -> None`. Sin SQL.
  - `services/licencias.LicenciaService(db, carpeta: Path)` con `verificar_acceso() -> EstadoLicencia`, `instalar_licencia(ruta) -> EstadoLicencia` y `max_usuarios() -> int`. Usa solo `carpeta / "licencia.apulic"` y `carpeta / ".trial.dat"`, la tabla `control_prueba` (ya creada por m0001) y `repos/empresas.actualizar_por_licencia(conn, ruc, empresa)`, que actualiza la primera empresa con el RUC y el nombre de la licencia.

- [ ] **Step 1: Escribir las pruebas que fallan:**
  - `test_clave_publica_intacta`: `PUBLIC_KEY_DER_B64` igual al valor de Global Constraints.
  - `test_rechaza_producto_ajeno`: portado del legado, usando `validar_payload`.
  - `test_licencia_valida_formato_1_4_0`: documento firmado con la clave de prueba, `product: "BAP APU Profesional"`, RUC de 11 dígitos, `max_users: 3` y el equipo parchado; se espera `modo == "LICENCIA"` y `max_usuarios == 3`.
  - `test_prueba_nueva_15_dias`: `verificar_acceso()` en base nueva da `modo == "PRUEBA"` y `dias_restantes` en (14, 15).
  - `test_detecta_fecha_atrasada`: con `control_prueba.ultimo_uso` 2 días en el futuro, se espera `modo == "BLOQUEADA"`.
  - `test_escribe_solo_en_su_carpeta` (Review Focus 5): tras `verificar_acceso()`, `.trial.dat` existe en `carpeta` y la carpeta `BAP_APU_Profesional` bajo `os.environ["LOCALAPPDATA"]` no contiene `.trial.dat`.
- [ ] **Step 2: Ejecutar:** `.venv/Scripts/python -m pytest tests/test_licencias.py -q`. Expected: FAIL.
- [ ] **Step 3: Implementar.**
- [ ] **Step 4: Ejecutar todo:** `.venv/Scripts/python -m pytest -q`. Expected: todo en verde.
- [ ] **Step 5: Commit:** `git add -A && git commit -m "Licencias offline aisladas en bap_apu.licensing"`

---

### Task 6: Empresa, configuración, dashboard, auditoría y terceros

**Files:**
- Create: `bap_apu/data/repos/empresas.py`, `bap_apu/data/repos/terceros.py`, `bap_apu/services/empresa.py`, `bap_apu/services/terceros.py`
- Test: `tests/test_empresa_terceros.py` (porta `test_empresa_clientes_proveedores_dashboard` de `tests/test_business.py`)

**Interfaces:**
- Consumes: `repos/auditoria`, `LicenciaService`, `Contexto`.
- Produces:
  - `repos/empresas`: `principal_de_usuario(conn, usuario_id)`, `actualizar(conn, empresa_id, ruc, razon_social, nombre_comercial, direccion, telefono, email)`, `configuracion(conn, empresa_id) -> dict`, `guardar_configuracion(conn, empresa_id, valores)`, `dashboard(conn, empresa_id) -> dict` (mismas claves que `obtener_dashboard`), junto a `actualizar_por_licencia` (creada en la tarea 5).
  - `repos/terceros`: `listar_clientes`, `insertar_cliente`, `listar_proveedores`, `insertar_proveedor`, `buscar_proveedor_por_ruc(conn, empresa_id, ruc)`, `buscar_proveedor_por_nombre(conn, empresa_id, nombre)` e `insertar_proveedor_minimo(conn, empresa_id, ruc, nombre) -> int` (las tres últimas, para la importación).
  - `services/empresa.EmpresaService(db, licencias: LicenciaService)` con:
    - `empresa_principal(usuario_id)`, sin `ctx`.
    - `guardar_empresa(ctx, ruc, razon_social, nombre_comercial, direccion, telefono, email)` y `guardar_configuracion(ctx, valores)`, que exigen `configuracion.gestionar`.
    - `obtener_configuracion(ctx)` y `estado_licencia(ctx)` (misma tupla de 7 elementos), que exigen `licencias.ver`.
    - `obtener_dashboard(ctx)`, que exige `dashboard.ver`.
    - `listar_auditoria(ctx, limite=300)`, que exige `auditoria.ver`.
  - `services/terceros.TercerosService(db)` con `listar_clientes(ctx)` [`clientes.ver`], `crear_cliente(ctx, tipo, numero, nombre, direccion, telefono, email)` [`clientes.editar`], `listar_proveedores(ctx)` [`proveedores.ver`] y `crear_proveedor(ctx, ruc, nombre, contacto, telefono, email)` [`proveedores.editar`]. Cada alta registra la auditoría en la misma transacción.

- [ ] **Step 1: Escribir las pruebas que fallan:** el caso portado, y además:
  - `test_razon_social_obligatoria`: se espera `ErrorValidacion`.
  - `test_ingeniero_no_crea_clientes`: se espera `PermisoDenegado`.
  - `test_alta_cliente_audita`: aparece `CLIENTE_CREADO` en `listar_auditoria`.
  - `test_estado_licencia_prueba`: `estado_licencia(ctx)[0] == "PRUEBA"`.
- [ ] **Step 2: Ejecutar:** `.venv/Scripts/python -m pytest tests/test_empresa_terceros.py -q`. Expected: FAIL.
- [ ] **Step 3: Implementar.**
- [ ] **Step 4: Ejecutar todo:** `.venv/Scripts/python -m pytest -q`. Expected: todo en verde.
- [ ] **Step 5: Commit:** `git add -A && git commit -m "Servicios de empresa y terceros"`

---

### Task 7: Proyectos, recursos, APU y biblioteca de partidas

**Files:**
- Create: `bap_apu/core/__init__.py`, `bap_apu/core/calculo.py`, `bap_apu/data/repos/proyectos.py`, `bap_apu/data/repos/recursos.py`, `bap_apu/data/repos/precios.py`, `bap_apu/data/repos/apu.py`, `bap_apu/data/repos/partidas.py`, `bap_apu/services/proyectos.py`, `bap_apu/services/recursos.py`, `bap_apu/services/apu.py`, `bap_apu/services/partidas.py`
- Test: `tests/test_calculo.py`, `tests/test_apu_servicios.py` (porta `tests/test_database.py`)

**Interfaces:**
- Produces:
  - `core/calculo.agrupar_subtotales(filas: Iterable[tuple[str, float | None]]) -> dict[str, float]`: misma normalización y claves (`"Mano de Obra"`, `"Materiales"`, `"Equipo"`) que `obtener_subtotales`, con redondeo a 2 decimales.
  - Repos (SQL y tuplas de `database.py`, siempre filtrando por `empresa_id`):
    - `proyectos`: `listar(conn, empresa_id)`, `insertar(conn, nombre, empresa_id) -> int`, `pertenece(conn, proyecto_id, empresa_id) -> bool` y `eliminar(conn, proyecto_id)`.
    - `recursos`: `listar(conn, empresa_id)`, `insertar(conn, nombre, unidad, precio, tipo, empresa_id, codigo=None, marca=None) -> int`, `existentes_para_importar(conn, empresa_id)`, `actualizar_datos(conn, recurso_id, empresa_id, codigo, marca, tipo)`, `precio(conn, recurso_id) -> float` y `actualizar_precio(conn, recurso_id, precio)`.
    - `precios`: `ofertas(conn, empresa_id, recurso_id)`, `oferta(conn, empresa_id, recurso_id, oferta_id)`, `insertar_oferta(conn, ...)` (columnas de la importación) y `registrar_historial(conn, empresa_id, recurso_id, proveedor_id, anterior, nuevo, origen)`.
    - `apu`: `detalle(conn, proyecto_id)`, `tipos_y_parciales(conn, proyecto_id)`, `total(conn, proyecto_id) -> float`, `insertar(conn, proyecto_id, nombre, unidad, precio, cantidad, tipo)` (parcial = `round(precio * cantidad, 2)`), `insertar_varios(conn, proyecto_id, filas)`, `proyecto_de_item(conn, detalle_id) -> int | None`, `eliminar_item(conn, detalle_id)` y `limpiar(conn, proyecto_id)`.
    - `partidas`: `listar(conn)` y `detalle(conn, partida_id)`.
  - Servicios (cada uno recibe `db`):
    - `ProyectosService`: `listar(ctx)` [`proyectos.ver`], `crear(ctx, nombre) -> int` [`proyectos.editar`] y `eliminar(ctx, proyecto_id)` [`proyectos.editar`, borra el detalle y el proyecto en una transacción].
    - `RecursosService`: `listar(ctx)` [`recursos.ver`], `crear(ctx, nombre, unidad, precio, tipo) -> int` [`recursos.editar`], `ofertas(ctx, recurso_id)` [`recursos.ver`] y `aplicar_oferta(ctx, recurso_id, oferta_id) -> float` [`recursos.editar`, origen `"SELECCION_PROVEEDOR"`].
    - `ApuService`: `detalle`, `subtotales` y `total(ctx, proyecto_id)` [`apu.ver`]; `agregar_item(ctx, proyecto_id, nombre, unidad, precio, cantidad, tipo)`, `eliminar_item(ctx, detalle_id)` y `limpiar(ctx, proyecto_id)` [`apu.editar`].
    - `PartidasService`: `listar(ctx)` y `detalle(ctx, partida_id)` [`partidas.ver`]; `cargar_en_proyecto(ctx, partida_id, proyecto_id) -> int` [`partidas.usar`, mensaje "La partida seleccionada no contiene recursos" si está vacía].
  - Regla común: si `proyecto_id` (o el proyecto de un `detalle_id`) no pertenece a `ctx.empresa_id`, se lanza `ErrorValidacion("El proyecto no existe o no pertenece a su empresa.")` sin escribir nada.

- [ ] **Step 1: Escribir las pruebas que fallan:**
  - `tests/test_calculo.py`: `agrupar_subtotales([("mano de obra ", 10), ("Materiales", 5.555), ("Equipos", 1), ("Herramientas", 9), ("Material", None)])` == `{"Mano de Obra": 10, "Materiales": 5.56, "Equipo": 1}`.
  - `tests/test_apu_servicios.py`: los 3 casos portados de `test_database.py`, y además:
    - `test_ids_de_otra_empresa_no_se_tocan` (Review Focus 4): crear una segunda empresa con su proyecto y un ítem; con `ctx_admin` (empresa 1), `eliminar_item`, `detalle`, `eliminar` y `cargar_en_proyecto` sobre esos IDs lanzan `ErrorValidacion`, y el ítem sigue existiendo.
    - `test_consulta_no_edita_apu`: se espera `PermisoDenegado`.
    - `test_aplicar_oferta_registra_historial`.
    - `test_total_fixture_1_4_0`: en la fixture con datos ya migrada, `total` de "Vivienda Los Pinos" es igual a `SUM(parcial)` leído directamente con SQL, y el tipo "Herramientas" no aparece en los subtotales.
- [ ] **Step 2: Ejecutar:** `.venv/Scripts/python -m pytest tests/test_calculo.py tests/test_apu_servicios.py -q`. Expected: FAIL.
- [ ] **Step 3: Implementar.**
- [ ] **Step 4: Ejecutar todo:** `.venv/Scripts/python -m pytest -q`. Expected: todo en verde.
- [ ] **Step 5: Commit:** `git add -A && git commit -m "Servicios de proyectos, recursos, APU y partidas con control por empresa"`

---

### Task 8: Importación de recursos y ofertas

**Files:**
- Create: `bap_apu/data/repos/importaciones.py`, `bap_apu/services/importacion_archivo.py`, `bap_apu/services/importacion.py`
- Test: `tests/test_importacion_servicio.py` (porta `tests/test_importacion.py`)

**Interfaces:**
- Consumes: `repos/recursos`, `repos/precios`, `repos/terceros` y `repos/auditoria`.
- Produces:
  - `importacion_archivo`: `COLUMNAS`, `ALIASES`, `TIPOS`, `normalizar_texto`, `normalizar_cabecera`, `numero`, `fecha` y `leer_archivo(ruta) -> list[tuple[int, dict]]`. Son copia literal de los helpers legados, sin el guion bajo inicial.
  - `repos/importaciones.registrar(conn, empresa_id, usuario_id, archivo, formato, filas, nuevos, actualizados, ofertas, omitidos)`.
  - `ImportacionService(db)` con `previsualizar(ctx, ruta) -> list[dict]` y `ejecutar(ctx, ruta) -> dict`, ambos con `recursos.editar`. Mismas claves de diccionario, mismas reglas y mismos mensajes que el legado; todo el SQL pasa por los repos. `ejecutar` es una sola transacción.

- [ ] **Step 1: Escribir las pruebas que fallan:** portar los casos de `test_importacion.py` y agregar:
  - `test_importacion_fallida_no_deja_rastros`: un CSV válido con un repo de precios parchado para que lance a la mitad; se espera la misma cantidad de `recursos` y de `importaciones_recursos` que antes.
  - `test_presupuestador_no_importa`: se espera `PermisoDenegado`.
- [ ] **Step 2: Ejecutar:** `.venv/Scripts/python -m pytest tests/test_importacion_servicio.py -q`. Expected: FAIL.
- [ ] **Step 3: Implementar.**
- [ ] **Step 4: Ejecutar todo:** `.venv/Scripts/python -m pytest -q`. Expected: todo en verde.
- [ ] **Step 5: Commit:** `git add -A && git commit -m "Servicio de importación separado de la lectura de archivos"`

---

### Task 9: Respaldos y restauración

**Files:**
- Create: `bap_apu/data/repos/respaldos.py`, `bap_apu/services/respaldos.py`
- Test: `tests/test_respaldos.py` (porta `tests/test_backup_restore.py` y el respaldo de `test_business.py`)

**Interfaces:**
- Consumes: `respaldar_sqlite`, `preparar_base`, `repos/auditoria` y `ErrorMigracion`.
- Produces:
  - `repos/respaldos.registrar(conn, usuario_id, ruta, hash_sha256, tamano)`.
  - `RespaldoService(db, carpeta_datos: Path)`:
    - `crear(ctx, destino) -> tuple[str, str]` [`respaldos.gestionar`]: escribe `APU_backup_{%Y%m%d_%H%M%S}.db` con `respaldar_sqlite`, registra el SHA-256 y audita `RESPALDO_CREADO`.
    - `restaurar(ctx, ruta) -> str` [`respaldos.gestionar`]: mismas validaciones y mensajes que el legado. Crea la copia de emergencia `BAP_APU_emergencia_{...}.db` con `respaldar_sqlite`, reemplaza el archivo con `os.replace` y llama a `preparar_base(db, carpeta_datos)`. Si eso lanza `ErrorMigracion`, vuelve a copiar la emergencia sobre la base y relanza. Si todo sale bien, audita `RESPALDO_RESTAURADO` y devuelve la ruta de la emergencia.

- [ ] **Step 1: Escribir las pruebas que fallan:** los 2 casos portados, el de creación con un hash de 64 caracteres, y además (Review Focus 3):
  - `test_restaurar_respaldo_1_4_0_lo_migra`: restaurar la fixture con datos; después `user_version == 1` y hay 2 proyectos.
  - `test_restaurar_tras_varias_operaciones`: antes de restaurar, llamar a `ApuService.total`, `ProyectosService.listar` y `EmpresaService.obtener_dashboard`; `restaurar` no debe lanzar `PermissionError`.
  - `test_migracion_fallida_vuelve_a_emergencia`: restaurar un respaldo con `user_version = 99`; se espera `ErrorMigracion`, y la base activa conserva los datos previos (mismo `nombre_comercial`).
- [ ] **Step 2: Ejecutar:** `.venv/Scripts/python -m pytest tests/test_respaldos.py -q`. Expected: FAIL.
- [ ] **Step 3: Implementar.**
- [ ] **Step 4: Ejecutar todo:** `.venv/Scripts/python -m pytest -q`. Expected: todo en verde.
- [ ] **Step 5: Commit:** `git add -A && git commit -m "Respaldos con API de SQLite y restauración que migra la base"`

---

### Task 10: Reportes PDF y Excel

**Files:**
- Create: `bap_apu/reports/__init__.py`, `bap_apu/reports/pdf.py`, `bap_apu/reports/excel.py`, `bap_apu/data/repos/reportes.py`, `bap_apu/services/reportes.py`
- Test: `tests/test_reportes.py` (porta el Excel de `test_business.py`; borrar `tests/test_business.py`)

**Interfaces:**
- Produces:
  - `reports/pdf.exportar_apu_pdf(nombre_proyecto, datos_apu, subtotales, total_general, ruta_guardado) -> None`: copia de `exportar_pdf.py` que usa `bap_apu.brand` y `bap_apu.paths.recurso`.
  - `reports/excel.HojaReporte(nombre_hoja: str, titulo: str, encabezados: list[str], filas: list[tuple])` y `reports/excel.escribir_libro(ruta, hojas: list[HojaReporte]) -> Path`, con el formato de `_hoja` legado (color `1F4E78`).
  - `repos/reportes`: `proyectos_resumen`, `recursos`, `partidas`, `precios_proveedores` e `historial_precios`, todas `(conn, empresa_id)` salvo `partidas(conn)`, con el SQL de `report_service.py`.
  - `ReportesService(db)` con:
    - `exportar_excel(ctx, ruta) -> Path` [`reportes.exportar`]: mismas 5 hojas, títulos y encabezados que el legado.
    - `exportar_apu_pdf(ctx, proyecto_id, nombre_proyecto, ruta) -> Path` [`apu.exportar`]: verifica que el proyecto sea de la empresa y lanza `ErrorValidacion("Este proyecto no tiene recursos asignados en el APU.")` si no tiene detalle.

- [ ] **Step 1: Escribir las pruebas que fallan:**
  - `test_excel_cinco_hojas`: hojas `["Resumen", "Recursos", "Partidas", "Precios Proveedores", "Historial Precios"]` y tamaño > 4000 bytes.
  - `test_pdf_generado`: sobre la fixture migrada, el archivo empieza con `b"%PDF"`.
  - `test_pdf_proyecto_vacio`: se espera `ErrorValidacion`.
- [ ] **Step 2: Ejecutar:** `.venv/Scripts/python -m pytest tests/test_reportes.py -q`. Expected: FAIL.
- [ ] **Step 3: Implementar.**
- [ ] **Step 4: Ejecutar todo:** `.venv/Scripts/python -m pytest -q`. Expected: todo en verde.
- [ ] **Step 5: Commit:** `git add -A && git commit -m "Reportes PDF y Excel desde servicios"`

---

### Task 11: Contenedor de servicios e interfaz conectada

**Files:**
- Create: `bap_apu/servicios.py`, `bap_apu/ui/__init__.py`, `bap_apu/ui/imagenes.py`, `bap_apu/ui/login.py`, `bap_apu/ui/app.py`, `bap_apu/ui/views/__init__.py` y un módulo por vista: `activacion.py`, `apu.py`, `configuracion.py`, `dashboard.py`, `partidas.py`, `proyectos.py`, `recursos.py`, `reportes.py`, `terceros.py`, `usuarios.py`
- Modify: `main.py` (reemplazo completo)
- Test: `tests/test_arquitectura.py`, `tests/test_ui_humo.py`

**Interfaces:**
- Consumes: todos los servicios de las tareas 4 a 10.
- Produces:
  - `servicios.Servicios`, dataclass congelada: `db`, `licencias`, `auth`, `empresa`, `terceros`, `proyectos`, `recursos`, `apu`, `partidas`, `importacion`, `respaldos` y `reportes`. Más `crear_servicios(db, carpeta_datos: Path) -> Servicios`.
  - `ui/imagenes.cargar_isotipo(tamano) -> ctk.CTkImage` (de `main.py`).
  - `ui/login.LoginWindow(servicios)` con `.run() -> UsuarioSesion | None`, y `ui/login.DialogoCambioPassword(parent, servicios, usuario_id, password_actual)` con `.mostrar() -> bool`.
  - `ui/app.AppAPU(servicios, sesion, ctx, estado_licencia)`, con `solicito_cerrar_sesion` como en el legado. `exportar_pdf` llama a `servicios.reportes.exportar_apu_pdf`.
  - Cada vista: `Vista*(parent, servicios, ctx)`, salvo `VentanaActivacion(servicios, estado)`. Las banderas `can_edit` y `can_export` salen de `ctx.puede(...)` con los mismos permisos que usa hoy `main.py`. El diseño visual se copia sin cambios (el rediseño es la Fase 3). Las llamadas a `database.*` y `services.*` legados se reemplazan por el método equivalente de las tareas 4 a 10.
  - `main.main() -> int`: arma `Database(paths.ruta_base_datos())`; llama a `preparar_base(db, paths.carpeta_datos())` y, ante `ErrorMigracion`, muestra `messagebox.showerror("No se pudo actualizar la base de datos", str(e))` y devuelve 1; luego `crear_servicios`; licencia y activación; ciclo de login. Mismo flujo que el `__main__` legado. El archivo termina con `if __name__ == "__main__": raise SystemExit(main())`.

- [ ] **Step 1: Escribir las pruebas que fallan:**
  - `tests/test_arquitectura.py`:
    - `test_ui_sin_sql`: ningún `.py` bajo `bap_apu/ui/` contiene `"import sqlite3"`, `"bap_apu.data"` ni las palabras `SELECT `, `INSERT `, `UPDATE ` o `DELETE ` en mayúsculas.
    - `test_core_puro`: `bap_apu/core/*.py` no importa `sqlite3`, `tkinter`, `customtkinter` ni `bap_apu.`.
    - `test_servicios_sin_tk`: `bap_apu/services/*.py` no importa `tkinter` ni `customtkinter`.
  - `tests/test_ui_humo.py`: con `ctk.CTk()` oculto (`withdraw`), construir cada vista con `crear_servicios(db, tmp_path)` y `ctx_admin`, llamar a `update()` y luego a `destroy()`. Construir también `AppAPU` con una sesión de admin. Si Tk no está disponible (`tkinter.TclError`), usar `pytest.skip`.
- [ ] **Step 2: Ejecutar:** `.venv/Scripts/python -m pytest tests/test_arquitectura.py tests/test_ui_humo.py -q`. Expected: FAIL.
- [ ] **Step 3: Implementar** el contenedor, el login, la app, las vistas y `main.py`.
- [ ] **Step 4: Ejecutar todo:** `.venv/Scripts/python -m pytest -q`. Expected: todo en verde.
- [ ] **Step 5: Prueba manual:** `.venv/Scripts/python main.py`. Iniciar sesión con admin/admin123, cambiar la contraseña, crear un proyecto, agregar un recurso al APU, exportar PDF y Excel, y crear y restaurar un respaldo. Expected: todo funciona como en la 1.4.0.
- [ ] **Step 6: Commit:** `git add -A && git commit -m "Interfaz conectada a servicios; main.py mínimo"`

---

### Task 12: Retiro del código legado y empaquetado 1.5.0

**Files:**
- Delete: `database.py`, `brand.py`, `version.py`, `exportar_pdf.py`, `services/`, `views/`, `security/`, `tests/test_database.py`, `tests/test_branding.py`, `tests/test_conexiones.py` y `tests/test_instalacion_db.py` (si quedan pruebas legadas sin portar, se portan aquí primero)
- Modify: `main.spec` (sin cambios de `datas`; agregar `hiddenimports=['bap_apu.ui.views']` solo si PyInstaller lo pide), `installer/BAP_APU_Profesional.iss` (`MyAppVersion "1.5.0"`, `OutputBaseFilename=Instalador_BAP_APU_Profesional_1.5.0`), `README.md` (estructura, `requirements-dev.txt` y cómo correr pruebas), `ESTADO_COMERCIAL.md`
- Create: `NOVEDADES_1.5.0.md`, `tests/test_marca.py`

**Interfaces:**
- Consumes: todo lo anterior.

- [ ] **Step 1: Escribir la prueba** `tests/test_marca.py`, que porta `test_branding.py`: identidad con versión `1.5.0`; que `main.py`, `bap_apu/reports/pdf.py` y `main.spec` no contengan `"D&D"` ni `"dyd.png"`; y que existan los assets. Agregar `test_sin_modulos_legados`: no existen `database.py`, `services/`, `views/` ni `exportar_pdf.py` en la raíz.
- [ ] **Step 2: Ejecutar:** `.venv/Scripts/python -m pytest tests/test_marca.py -q`. Expected: FAIL (`test_sin_modulos_legados`).
- [ ] **Step 3: Borrar lo legado y actualizar el empaquetado y la documentación.** `NOVEDADES_1.5.0.md` explica en lenguaje de cliente que la base se actualiza sola con respaldo previo en `respaldos\`, que la restauración de respaldos es más confiable y que no hay cambios de uso.
- [ ] **Step 4: Ejecutar todo:** `.venv/Scripts/python -m pytest -q`. Expected: todo en verde y `grep -rn "from database\|import database" bap_apu main.py tests` sin resultados.
- [ ] **Step 5: Construir:** `.venv/Scripts/python -m pip install pyinstaller` y luego `.venv/Scripts/python -m PyInstaller --clean --noconfirm main.spec`. Expected: existe `dist/BAP_APU_Profesional/BAP_APU_Profesional.exe`; al abrirlo, inicia sesión y exporta un PDF. Compilar el `.iss` con Inno Setup si está instalado; si no, dejarlo anotado como pendiente.
- [ ] **Step 6: Commit:** `git add -A && git commit -m "Versión 1.5.0: retiro del código legado y empaquetado"`

---

### Task 13: Publicar en un repositorio nuevo de GitHub

Pedido explícito del usuario. **Antes de ejecutar, confirmar con el usuario el nombre del repositorio y su visibilidad** (se recomienda privado: contiene la lógica de licencias).

**Files:** ninguno (solo git y gh).

- [ ] **Step 1: Verificar** que `.gitignore` excluye `apu.db`, `.venv/`, `build/` y `dist/`, y que no se versionan claves privadas: `git ls-files | grep -iE "\.pem|private|\.apulic"` debe salir vacío.
- [ ] **Step 2: Crear y subir:** `gh repo create guardiapetitgustavo-max/<nombre> --private --source . --remote origin --push`. Expected: la URL del repositorio, y `git status` dice "up to date with 'origin/main'".
- [ ] **Step 3: Confirmar:** `gh repo view guardiapetitgustavo-max/<nombre> --json visibility,url`.
