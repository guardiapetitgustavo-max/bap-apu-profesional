# Estado comercial de BAP APU Profesional 1.4.0

## Cambios aplicados

- Identidad comercial centralizada en `brand.py`.
- Nombre BAP APU Profesional y versión 1.4.0.
- Logo BAP en acceso, menú, ejecutable, instalador y PDF.
- Colores BAP en reportes.
- Contacto y sitio web de BAP en el sistema y PDF.
- Carpeta de datos separada de la edición D&D.
- Base demostrativa identificada como Constructora Demo S.A.C.
- Creación y restauración validada de respaldos.
- Copia de emergencia antes de cada restauración.
- Nombres comerciales para ejecutable e instalador.

## Validaciones pendientes en Windows

1. Generar el ejecutable con PyInstaller.
2. Probar en una instalación limpia de Windows 10 y Windows 11.
3. Compilar el instalador con Inno Setup.
4. Probar activación con una licencia `.apulic` de demostración.
5. Confirmar que las licencias firmadas actuales siguen siendo compatibles.
6. Revisar SmartScreen; mientras no exista firma de código, explicar al cliente cómo validar el editor.

## Decisión importante de licenciamiento

La clave pública Ed25519 existente se conservó para no romper el generador de
licencias. La clave privada nunca debe incluirse en el instalador ni entregarse
al cliente. El marcador local de prueba y la carpeta de datos usan nombres BAP,
por lo que esta edición no interfiere con la edición exclusiva de D&D.
