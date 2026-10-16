# Reestructuración de BAP APU Profesional — Documento de diseño

- **Fecha:** 2026-10-16
- **Versión de partida:** 1.4.0 (commit `71fd64f`)
- **Versiones objetivo:** 1.5.0 (Fase 1), 2.0.0 (Fase 2), 2.1.0 (Fase 3)
- **Enfoque aprobado:** A — refactor incremental, por fases, cada una instalable

## 1. Contexto

BAP APU Profesional es una aplicación de escritorio para Windows (Python, customtkinter,
SQLite, ReportLab, openpyxl) para el análisis de precios unitarios en construcción. Tiene
unas 3.300 líneas, autenticación con roles y permisos, multiempresa, licencias offline
firmadas con Ed25519 (`.apulic`), importación de recursos desde Excel/CSV, comparación de
ofertas de proveedores, respaldos, exportación PDF/Excel e instalador (PyInstaller + Inno
Setup). Hay clientes usando la 1.4.0 con datos reales.

### Problemas detectados

1. **Modelo de APU incorrecto.** `detalle_apu` cuelga del *proyecto*, no de una *partida*.
   No existe presupuesto con metrados. La biblioteca de partidas guarda rendimiento y
   cuadrilla, pero al cargarla se copian cantidades fijas y se pierden. No hay
   herramientas como % de mano de obra, ni gastos generales, utilidad o IGV.
2. **Precios desconectados.** Cada ítem del APU copia nombre y precio del recurso. Al
   actualizar un precio (o elegir una oferta de proveedor) los APU no se recalculan.
3. **Arquitectura mezclada.** `database.py` (686 líneas) combina ruta de la base, esquema,
   migraciones ad hoc (`_agregar_columna_si_falta`), semillas y consultas. Las vistas
   importan funciones SQL directamente. `main.py` contiene login, cambio de contraseña y
   ventana principal. Conexiones abiertas y cerradas a mano en estilos distintos.
   `DB_PATH` se calcula al importar el módulo.
4. **Permisos solo en la interfaz.** Los servicios no verifican permisos; solo se ocultan
   botones.
5. **Integridad.** `detalle_apu` sin claves foráneas ni empresa. La biblioteca de partidas
   es global (sin `empresa_id`).
6. **Interfaz.** Colores y fuentes escritos a mano en cada vista. `CTkOptionMenu` como
   selector de recursos (no sirve con cientos de ítems). Sin tablas reutilizables.

## 2. Objetivos y no objetivos

### Objetivos

- Código en capas con dependencias en una sola dirección, probado y fácil de extender.
- Modelo de presupuesto y APU fiel a la práctica peruana (estilo S10).
- Interfaz moderna, audaz y consistente con la marca BAP.
- **Cero pérdida de datos**: toda base 1.4.0 se migra automáticamente, con respaldo
  previo, y los totales de los proyectos existentes se conservan al centavo.
- Las licencias `.apulic` ya emitidas siguen funcionando (misma clave pública Ed25519).

### No objetivos (fuera de alcance)

- Versión web, sincronización en la nube o modo multiusuario en red.
- Cambiar el esquema de licenciamiento o el generador privado de licencias.
- Firma de código del ejecutable (SmartScreen).
- Cronograma, fórmula polinómica, metrados desde planos, valorizaciones. Quedan como
  posibles módulos futuros sobre el modelo de la Fase 2.

## 3. Supuestos (confirmar o corregir)

- Metodología peruana: jornada de **8 horas**, **IGV 18 %**, herramientas manuales como
  porcentaje de la mano de obra, GG y utilidad como porcentaje del costo directo. Todos
  configurables por presupuesto, con valores por defecto por empresa.
- Se mantiene customtkinter como base de la interfaz. Las tablas usan `ttk.Treeview` con
  estilo propio.
- Se mantiene `unittest` como estilo de pruebas, ejecutadas con `pytest` (dependencia solo
  de desarrollo en `requirements-dev.txt`).
- La clave privada de licencias nunca entra a este repositorio.

## 4. Arquitectura objetivo

```
bap-apu/
├── main.py                      # punto de entrada mínimo: arma la app y la ejecuta
├── bap_apu/
│   ├── brand.py                 # identidad, versión, contacto
│   ├── paths.py                 # rutas de recursos empaquetados y carpeta de datos
│   ├── contexto.py              # Contexto(usuario, empresa_id, permisos)
│   ├── errores.py               # ErrorValidacion, PermisoDenegado, etc.
│   ├── core/                    # dominio puro: sin UI, sin SQL
│   │   ├── modelos.py           # dataclasses: Insumo, Apu, Partida, Presupuesto...
│   │   └── calculo.py           # fórmulas de APU y presupuesto (Decimal)
│   ├── data/
│   │   ├── db.py                # clase Database: ruta, conectar(), transaccion()
│   │   ├── instalacion.py       # base inicial del cliente (lógica actual)
│   │   ├── migraciones/
│   │   │   ├── runner.py        # PRAGMA user_version + respaldo previo
│   │   │   ├── m0001_esquema_1_4_0.py
│   │   │   └── m0002_presupuestos.py      # Fase 2
│   │   └── repos/               # una clase por agregado, solo SQL
│   ├── services/                # reglas de negocio, permisos, auditoría
│   ├── licensing/               # offline_license (sin cambios funcionales)
│   ├── security/                # passwords
│   ├── reports/                 # pdf.py, excel.py
│   └── ui/
│       ├── app.py               # ventana principal y navegación
│       ├── login.py             # login y cambio de contraseña
│       ├── theme.py             # Fase 3: tokens de color, tipografía, espaciado
│       ├── widgets/             # Fase 3: TablaDatos, SelectorBuscable, etc.
│       └── views/               # una vista por módulo
├── tests/
├── installer/  assets/  data/  templates/  ejemplos/
└── docs/
```

### Reglas de dependencia

```
ui  ──►  services  ──►  repos  ──►  data.db
              │
              └──►  core  (no depende de nada del proyecto)
```

- `ui` nunca importa `repos` ni ejecuta SQL.
- `services` recibe un `Contexto` y verifica permisos (`PermisoDenegado`) además de la UI.
- `repos` no conoce permisos ni auditoría; solo lee y escribe.
- `core` es Python puro y se prueba sin base de datos.
- La instancia de `Database` se crea al iniciar la app y se inyecta en los servicios. Ya
  no hay `DB_PATH` global; las pruebas pasan una base temporal.

## 5. Fase 1 — Cimientos (1.5.0)

**Meta:** misma funcionalidad visible que la 1.4.0, nueva estructura interna.

### Alcance

1. Crear el paquete `bap_apu/` y mover los módulos según la sección 4.
2. Dividir `database.py`:
   - Ruta e instalación → `data/db.py` y `data/instalacion.py` (misma lógica de
     `%LOCALAPPDATA%\BAP_APU_Profesional\apu.db`, semilla y legado).
   - Esquema actual y semillas → migración `m0001_esquema_1_4_0` (idempotente, reproduce
     exactamente `crear_tablas()` de la 1.4.0, incluidas las columnas agregadas).
   - Consultas → repositorios: `ProyectosRepo`, `RecursosRepo`, `ApuRepo`,
     `PartidasRepo`, `PreciosRepo`, `UsuariosRepo`, `EmpresasRepo`, `TercerosRepo`,
     `AuditoriaRepo`, `ConfiguracionRepo`, `LicenciasRepo`.
3. **Migraciones versionadas** con `PRAGMA user_version`:
   - Al iniciar, el runner lee la versión. Si es menor que la requerida, primero crea
     `respaldos\pre_migracion_v{N}_{AAAAMMDD_HHMMSS}.db` en la carpeta de datos usando la
     API de backup de SQLite, verifica `integrity_check` y luego aplica cada migración
     pendiente en su propia transacción.
   - Base 1.4.0 (versión 0 con tablas existentes) → se aplica `m0001` (no destructiva) y
     queda en versión 1.
   - Si una migración falla: rollback, mensaje claro al usuario con la ruta del respaldo,
     y la app no continúa.
4. Separar `main.py`: `ui/login.py` (login + cambio de contraseña), `ui/app.py`
   (ventana principal y navegación), `main.py` solo arranca.
5. `Contexto` y verificación de permisos en servicios.
6. Vistas: reemplazar imports de `database` por llamadas a servicios.
7. Pruebas existentes adaptadas a la nueva estructura y en verde.
8. Actualizar `main.spec` e instalador a las nuevas rutas; versión 1.5.0.

### Correcciones permitidas en esta fase

Solo defectos confirmados con una prueba que primero falla. Candidatos a revisar:
filtrado de proyectos por empresa en todas las consultas, eliminación de detalle APU sin
verificar empresa, y conexiones no cerradas ante excepciones.

### Criterios de aceptación

- Todas las pruebas pasan; nueva cobertura para el runner de migraciones y los repos.
- Una copia de `data/apu_seed.db` y una base 1.4.0 de prueba con datos abren en 1.5.0,
  quedan en `user_version = 1`, se crea el respaldo y los datos quedan intactos.
- Ningún archivo en `ui/` contiene SQL ni importa `data.repos`.
- El ejecutable PyInstaller arranca, inicia sesión y exporta PDF como en la 1.4.0.

## 6. Fase 2 — Modelo APU real (2.0.0)

### 6.1 Modelo de datos (migración `m0002_presupuestos`)

```
proyectos (existente)
  └── presupuestos            id, empresa_id, proyecto_id, nombre, fecha, moneda,
                              jornada_horas (8), pct_gastos_generales, pct_utilidad,
                              pct_igv (18), estado, creado_en
        └── presupuesto_items id, presupuesto_id, padre_id (NULL = raíz), orden,
                              codigo ("01.02.03"), tipo ('TITULO' | 'PARTIDA'),
                              descripcion, unidad, metrado
              └── apus        id, item_id UNIQUE, rendimiento, unidad_rendimiento
                              (p. ej. m3/día), pct_herramientas (default 3)
                    └── apu_insumos  id, apu_id, recurso_id NULL, tipo
                              ('MANO_OBRA'|'MATERIAL'|'EQUIPO'|'SUBCONTRATO'),
                              descripcion, unidad, cuadrilla NULL, cantidad NULL,
                              precio_fijo NULL, orden
apu_plantillas (biblioteca)   id, empresa_id NULL (NULL = biblioteca BAP), descripcion,
                              unidad, rendimiento, pct_herramientas, fuente
  └── apu_plantilla_insumos   misma forma que apu_insumos
```

- Todas las tablas nuevas con `FOREIGN KEY ... ON DELETE CASCADE` hacia su padre y
  `empresa_id` donde corresponda.
- `presupuesto_items` con `padre_id` permite títulos y subtítulos anidados.
- `apu_insumos.recurso_id` enlaza al catálogo. Si `precio_fijo` es NULL, el precio se
  lee del recurso en el momento del cálculo; así, actualizar un recurso o aplicar una
  oferta de proveedor recalcula todos los APU. `precio_fijo` permite congelar un precio.
- Insumo **por cuadrilla** (`cuadrilla` no nulo, para mano de obra y equipo) o **por
  cantidad directa** (`cantidad` no nulo, para materiales, subcontratos o equipo por
  unidad). Restricción: exactamente uno de los dos.

### 6.2 Fórmulas (`core/calculo.py`, con `Decimal`)

| Concepto | Fórmula | Redondeo |
|---|---|---|
| Cantidad por cuadrilla | `cuadrilla × jornada_horas / rendimiento` | 4 decimales |
| Parcial de insumo | `cantidad × precio` | 2 decimales |
| Herramientas manuales | `pct_herramientas % × Σ parciales de mano de obra` | 2 decimales |
| Precio unitario (PU) | `Σ parciales + herramientas` | 2 decimales |
| Parcial de partida | `metrado × PU` | 2 decimales |
| Título | `Σ parciales de sus hijos` | — |
| Costo directo (CD) | `Σ parciales de partidas` | 2 decimales |
| Gastos generales | `CD × pct_gastos_generales %` | 2 decimales |
| Utilidad | `CD × pct_utilidad %` | 2 decimales |
| Subtotal | `CD + GG + Utilidad` | — |
| IGV | `Subtotal × pct_igv %` | 2 decimales |
| Total | `Subtotal + IGV` | — |

Redondeo `ROUND_HALF_UP`. Validaciones: rendimiento > 0 si hay insumos por cuadrilla;
metrado ≥ 0; porcentajes entre 0 y 100.

Salidas adicionales del motor:

- **Insumos consolidados del presupuesto:** Σ (cantidad × metrado) por recurso, con
  costo total, agrupado por tipo.
- Horas-hombre totales por categoría de mano de obra.

### 6.3 Migración de datos 1.x → 2.0

Para cada proyecto con filas en `detalle_apu`:

1. Crear un `presupuesto` "Presupuesto migrado" (GG 0 %, utilidad 0 %, IGV 0 %, para que
   el total coincida con el de la 1.4.0; el usuario los ajusta después).
2. Crear un ítem `PARTIDA` "APU migrado", unidad `glb`, metrado 1.
3. Crear su `apu` con `pct_herramientas = 0` y rendimiento NULL.
4. Cada fila de `detalle_apu` pasa a `apu_insumos` con `cantidad` directa y
   `precio_fijo` = precio original. Si existe un recurso de la misma empresa con igual
   nombre y unidad (sin distinguir mayúsculas), se enlaza `recurso_id` (el precio sigue
   fijo para no alterar totales).
5. El tipo de texto libre se normaliza con la misma lógica de `obtener_subtotales()`.

La biblioteca `partidas`/`partida_detalle` pasa a `apu_plantillas` (empresa NULL),
conservando cuadrilla, rendimiento y cantidades.

Las tablas `detalle_apu`, `partidas` y `partida_detalle` **no se borran** en 2.0: quedan
de solo lectura como respaldo y se eliminan en una versión posterior.

**Verificación obligatoria:** una prueba recorre cada proyecto migrado y comprueba que el
total 2.0 sea igual a `obtener_total()` de la 1.4.0, al centavo.

### 6.4 Funciones y servicios

- `PresupuestoService`: crear, duplicar, editar parámetros, árbol de títulos y partidas
  (agregar, mover, renumerar), calcular resumen.
- `ApuService`: editar rendimiento e insumos, cargar desde plantilla (enlaza recursos por
  código o por nombre más unidad; si no encuentra, crea el insumo con `precio_fijo` y lo
  marca para revisión), guardar un APU como plantilla.
- Nuevos permisos: `presupuestos.ver`, `presupuestos.editar`; mapeo a roles existentes
  (Ingeniero y Presupuestador editan; Consulta ve).

### 6.5 Reportes

- PDF: presupuesto (árbol con metrado, PU y parcial, más resumen CD/GG/U/IGV), APU por
  partida (formato S10: rendimiento, cuadrilla, cantidad, precio, parcial por grupo) y
  lista de insumos consolidados.
- Excel: las mismas tres hojas, más las existentes de ofertas e historial.

### Criterios de aceptación

- Pruebas del motor con casos calculados a mano, incluido al menos un APU de la
  biblioteca original reproducido con rendimiento y cuadrilla.
- Prueba de migración con totales idénticos en todas las bases de prueba.
- Cambiar el precio de un recurso cambia el PU de los APU enlazados sin precio fijo.
- Licencia `.apulic` de prueba de la 1.4.0 activa correctamente en 2.0.

## 7. Fase 3 — Interfaz (2.1.0)

### Dirección visual

Audaz y colorida, coherente con la marca BAP (teal y dorado de `brand.py`) sobre fondo
oscuro, con acentos de alto contraste por tipo de insumo (mano de obra, material,
equipo y subcontrato, cada uno con su color). Debe poder pasarse a tema claro.

### Componentes (`ui/widgets/`)

- `theme.py`: tokens únicos (colores, tipografía, espaciado, radios). Ninguna vista
  escribe colores ni fuentes a mano.
- `TablaDatos`: `ttk.Treeview` estilizado con búsqueda, orden por columna, formato de
  moneda, filas alternas, menú contextual y vista de árbol (para el presupuesto).
- `SelectorBuscable`: campo con autocompletado sobre recursos (código, nombre o
  unidad), navegable por teclado.
- `TarjetaIndicador`, `Notificacion` (aviso breve no bloqueante en vez de muchos
  `messagebox`) y `DialogoFormulario` con validación en línea.

### Pantallas

- **Navegación lateral** con secciones e iconos, ordenada según el flujo de trabajo:
  Presupuestos → APU → Recursos → Proveedores → Reportes → Administración.
- **Editor de presupuesto:** árbol de títulos y partidas a la izquierda y APU de la
  partida seleccionada a la derecha, con recálculo en vivo del PU y del total.
- **Dashboard:** indicadores reales (presupuestos activos, monto total, recursos con
  precio desactualizado, últimas importaciones) y un gráfico simple en canvas.
- Atajos de teclado: nuevo, buscar, guardar, exportar.

### Criterios de aceptación

- Ninguna vista define colores ni fuentes fuera de `theme.py`.
- Selector de recursos fluido con 5.000 recursos de prueba.
- Recorrido completo (crear presupuesto, agregar partidas desde plantilla, ajustar
  rendimiento, exportar PDF) sin usar el mouse para elegir recursos.

## 8. Compatibilidad, licencias y distribución

- `licensing/` conserva `PUBLIC_KEY_DER_B64`, el formato `.apulic`, el marcador de
  prueba y la carpeta de datos. Pruebas de regresión con una licencia generada para la
  1.4.0.
- La actualización del instalador nunca toca `%LOCALAPPDATA%\BAP_APU_Profesional\`.
- Riesgo conocido, no se cambia en este proyecto: el secreto HMAC del marcador de prueba
  está en el código (limitación inherente a un esquema offline).

## 9. Estrategia de pruebas

- `core/`: pruebas unitarias puras con resultados calculados a mano.
- `repos` y `services`: base SQLite temporal por prueba (fixture compartida).
- Migraciones: bases de prueba en `tests/fixtures/` (semilla 1.4.0 y una base sintética
  con varios proyectos, tipos escritos de formas distintas y recursos sin código).
- UI: prueba de humo que construye cada vista sin errores (sin interacción).
- Cada fase termina con el ejecutable PyInstaller probado manualmente en Windows.

## 10. Riesgos y mitigaciones

| Riesgo | Mitigación |
|---|---|
| Pérdida de datos al migrar | Respaldo automático verificado, transacción por migración, tablas viejas conservadas, prueba de totales |
| Regresiones al mover código en la Fase 1 | Fase sin cambios funcionales, pruebas en verde en cada paso, commits pequeños |
| Diferencias de redondeo con S10 | Reglas explícitas (sección 6.2) y casos de referencia en pruebas |
| Rendimiento de customtkinter con tablas grandes | `ttk.Treeview` en lugar de widgets por fila |
| Licencias existentes dejan de validar | Clave pública intacta y prueba de regresión |

## 11. Orden de entrega

Cada fase tiene su propio plan de implementación, su rama y su versión instalable. La
Fase 2 empieza solo cuando la 1.5.0 esté aprobada, y la Fase 3 cuando la 2.0.0 lo esté.
