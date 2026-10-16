# BAP APU Profesional 1.4.0 - edición comercial offline

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

## Ejecutar la aplicación

```powershell
py -m venv .venv
.venv\Scripts\activate
py -m pip install -r requirements.txt
py main.py
```

Acceso inicial: usuario `admin`, contraseña temporal `admin123`. El sistema
obliga a cambiarla inmediatamente.

## Crear ejecutable e instalador

```powershell
py -m pip install pyinstaller
py -m PyInstaller --clean --noconfirm main.spec
```

Abra `installer/BAP_APU_Profesional.iss` con Inno Setup y pulse **Compile**. El
instalador resultante se llamará `Instalador_BAP_APU_Profesional_1.4.0.exe`.

No requiere servidor, dominio, conexión permanente ni pasarela de pagos.
El cliente puede pagar mediante Yape, Plin o transferencia y recibir su archivo
de activación por correo o mensajería.

## Contacto BAP

- WhatsApp: +51 904 170 143
- Correo: contacto.bapsoluciones@gmail.com
- Web: https://bap-soluciones-tecnologicas.quick-spark-9180.chatgpt.site
