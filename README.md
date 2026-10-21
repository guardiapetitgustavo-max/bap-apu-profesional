# BAP APU Profesional 1.5.0 - edición comercial offline

Aplicación de BAP Soluciones Tecnológicas para el análisis de precios
unitarios en Windows 10 y Windows 11 de 64 bits.

## Funciones incluidas

- Dashboard ejecutivo con proyectos, clientes, recursos, partidas y costos.
- Empresas y separación de información por organización.
- Usuarios, roles, permisos, sesiones, bloqueo y auditoría.
- Clientes y proveedores.
- Proyectos, recursos, APU y biblioteca de 19 partidas.
- Exportación profesional a PDF y Excel.
- Configuración empresarial y moneda.
- Creación y restauración segura de respaldos, con validación SQLite y copia de emergencia.
- Planes, licencia de prueba y control de vencimiento.
- Control de versión y punto de conexión para actualizaciones.
- Importación masiva de recursos y ofertas desde Excel o CSV.
- Vista previa con validación de filas antes de confirmar cambios.
- Comparación de precios, calidad, stock y entrega por proveedor.
- Selección controlada de una oferta como precio vigente e historial de cambios.
- Especificaciones para PyInstaller e Inno Setup.

## Licenciamiento sin servidor

- Prueba gratuita de 15 días desde el primer inicio.
- Licencia vinculada al RUC y firmada digitalmente.
- Hasta 5 computadoras indicadas en el archivo `.apulic`.
- Hasta 5 usuarios activos.
- Activación y renovación sin Internet.
- Los datos permanecen guardados cuando vence la prueba o licencia.
- La base personal se guarda en `%LOCALAPPDATA%\BAP_APU_Profesional\apu.db`.
- Las actualizaciones del aplicativo no reemplazan la información del cliente.

## Estructura del proyecto

- `main.py`: punto de entrada mínimo (arranque, licencia, inicio de sesión).
- `bap_apu/core/`: cálculo puro, sin base de datos ni interfaz.
- `bap_apu/data/`: base de datos, migraciones, semillas y repositorios (todo el SQL).
- `bap_apu/services/`: reglas de negocio y permisos.
- `bap_apu/ui/`: interfaz customtkinter (`app.py`, `login.py`, `views/`); nunca toca SQL.
- `bap_apu/licensing/`, `bap_apu/reports/`, `bap_apu/security/`: licencias, PDF/Excel y contraseñas.
- `bap_apu/servicios.py`: contenedor que arma todos los servicios al iniciar.

## Ejecutar la aplicación

```powershell
py -m venv .venv
.venv\Scripts\activate
py -m pip install -r requirements.txt
py main.py
```

Acceso inicial: usuario `admin`, contraseña temporal `admin123`. El sistema
obliga a cambiarla inmediatamente.

## Ejecutar las pruebas

```powershell
py -m pip install -r requirements-dev.txt
.venv\Scripts\python -m pytest -q
```

## Crear ejecutable e instalador

```powershell
py -m pip install pyinstaller
py -m PyInstaller --clean --noconfirm main.spec
```

Abra `installer/BAP_APU_Profesional.iss` con Inno Setup y pulse **Compile**. El
instalador resultante se llamará `Instalador_BAP_APU_Profesional_1.5.0.exe`.

No requiere servidor, dominio, conexión permanente ni pasarela de pagos.
El cliente puede pagar mediante Yape, Plin o transferencia y recibir su archivo
de activación por correo o mensajería.

## Contacto BAP

- WhatsApp: +51 904 170 143
- Correo: contacto.bapsoluciones@gmail.com
- Web: https://bap-soluciones-tecnologicas.quick-spark-9180.chatgpt.site

## Versión web: suscripción y pagos

La web (`web/`) usa Supabase. Cada empresa tiene en la tabla `empresas`:

- `plan`: `prueba`, `basico`, `pro` o `empresa`.
- `prueba_hasta`: fin de la prueba gratis (por defecto, 15 días después del registro).
- `activa_hasta`: fecha hasta la que está pagado el plan.

Si `now()` pasa de `prueba_hasta` y de `activa_hasta`, la empresa queda en **solo lectura**.
La regla se aplica en la base de datos, dentro de la función `puede()` que usan las políticas
RLS. La app además muestra un banner con los planes y un botón de WhatsApp (+51 904 170 143).
Los usuarios no pueden cambiar `plan`, `prueba_hasta` ni `activa_hasta`, porque solo tienen
permiso de UPDATE sobre `razon_social` y `ruc`.

**Activar un plan después del pago (Yape, Plin o transferencia).** En Supabase, abre SQL Editor y ejecuta:

```sql
update public.empresas
   set plan = 'pro', activa_hasta = greatest(coalesce(activa_hasta, now()), now()) + interval '1 month'
 where ruc = '20XXXXXXXXX';   -- o: where razon_social ilike '%nombre%'
```

### Agregar una pasarela de pagos más adelante (Culqi o Mercado Pago)

Todavía no hay pasarela integrada porque hacen falta credenciales del comercio. Para agregarla:

1. Crea la cuenta de comercio en Culqi (https://culqi.com) o en Mercado Pago (https://www.mercadopago.com.pe/developers).
   Guarda la llave secreta como secreto de Edge Functions: `CULQI_SECRET_KEY` o `MP_ACCESS_TOKEN`.
2. **Checkout:** crea una Edge Function `crear-pago`. Debe validar el JWT del usuario y crear el cargo
   (Culqi: `POST https://api.culqi.com/v2/charges` con el token de Culqi.js) o la preferencia
   (Mercado Pago: `POST https://api.mercadopago.com/checkout/preferences`, con
   `external_reference = empresa_id` y `notification_url` apuntando al webhook).
3. **Webhook:** crea una Edge Function `webhook-pagos` con `verify_jwt = false`. Debe verificar la firma
   del proveedor (Mercado Pago usa el encabezado `x-signature`) y consultar el pago en su API.
   Si el pago está aprobado, actualiza `empresas.plan` y `activa_hasta` con la *service role key*.
4. En `app.js`, en `bannerSuscripcion()`, cambia los enlaces de WhatsApp por botones que llamen a
   `sb.functions.invoke("crear-pago", { body: { plan } })` y redirijan al checkout.

## Versión web: asistente IA de APU

La Edge Function `sugerir-apu` (`supabase/functions/sugerir-apu/index.ts`) recibe la descripción
de una partida y los recursos de la empresa. Llama a la API de Anthropic con el modelo `claude-sonnet-5-5`
y devuelve unidad, rendimiento, % de herramientas e insumos, usando los recursos existentes
cuando coinciden. Necesita el secreto `ANTHROPIC_API_KEY`: en Supabase, ve a
**Edge Functions → Secrets** y agrega `ANTHROPIC_API_KEY` con tu clave de https://console.anthropic.com.
Sin el secreto, la función responde con un error claro y la app lo muestra.
