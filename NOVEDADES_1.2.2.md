# Novedades de BAP APU Profesional 1.2.2

## Instalación comercial segura

- Incluye una base maestra con 55 recursos y 19 partidas.
- No distribuye proyectos, clientes, proveedores, sesiones ni auditorías de demostración.
- En el primer inicio copia la base a `%LOCALAPPDATA%\BAP_APU_Profesional\apu.db`.
- Si la base personal ya existe, nunca la reemplaza.
- Si encuentra una base de una instalación 1.2.1 junto al ejecutable, la migra automáticamente.
- Las futuras actualizaciones pueden reemplazar el programa sin eliminar los datos del cliente.

## Recompilación requerida

La versión 1.2.2 requiere generar nuevamente el ejecutable con `main.spec` y después
compilar `installer\BAP_APU_Profesional.iss` con Inno Setup.

Antes de distribuir, instale en una PC de prueba y confirme que el catálogo inicial aparece,
que no existen proyectos previos y que los datos continúan después de actualizar o reinstalar.
