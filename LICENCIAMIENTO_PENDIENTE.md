# Licenciamiento de BAP APU Profesional

El cliente conserva la clave pública Ed25519 de la versión entregada. Esto permite validar
las licencias `.apulic` existentes sin exponer una clave privada dentro del aplicativo.

## Antes de vender la primera licencia

1. Conservar el generador y la clave privada únicamente en un equipo administrativo de BAP.
2. Emitir una licencia de prueba para un equipo Windows real.
3. Validar activación, fecha de vencimiento, RUC y cantidad de usuarios.
4. Guardar una copia cifrada de la clave privada fuera del equipo de desarrollo.

Desde la versión 1.2.1, BAP cuenta con un generador privado independiente y un nuevo par de
claves Ed25519. La clave privada cifrada nunca debe incluirse en el instalador del cliente.
