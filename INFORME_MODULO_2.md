# Informe técnico - Módulo 2

## Funciones implementadas

- Usuarios almacenados en SQLite, sin credenciales escritas en la interfaz.
- Contraseñas protegidas mediante Scrypt con salt aleatorio.
- Cambio obligatorio de la contraseña temporal en el primer acceso.
- Roles: Administrador, Gerente, Ingeniero, Presupuestador y Consulta.
- Permisos separados para ver, editar, usar partidas, exportar y administrar usuarios.
- Bloqueo temporal durante 15 minutos después de cinco intentos fallidos.
- Registro de inicio, fallo, cierre, cambio de contraseña y gestión de cuentas.
- Pantalla administrativa para crear, activar y desactivar usuarios.
- Cierre de sesión y retorno seguro a la pantalla de acceso.

## Controles de seguridad

- El administrador no puede desactivar su propia cuenta mientras está conectado.
- Cada usuario nuevo debe cambiar su contraseña temporal.
- Las contraseñas requieren al menos ocho caracteres, mayúscula, minúscula y número.
- El rol Consulta tiene interfaz de solo lectura.
- Las sesiones poseen tokens aleatorios y registran inicio y finalización.

## Datos preservados

- 1 proyecto original.
- 55 recursos.
- 8 registros del APU original.
- 19 partidas maestras y 161 filas de detalle.
