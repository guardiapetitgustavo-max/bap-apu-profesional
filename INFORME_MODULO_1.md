# Informe técnico — Módulo 1

## Diagnóstico inicial

- Aplicación de escritorio en Python 3.14, CustomTkinter y SQLite.
- Funciones existentes: acceso temporal, proyectos, recursos, detalle APU,
  subtotales y exportación PDF.
- Datos recibidos: 1 proyecto, 8 recursos y 8 partidas APU.
- El archivo recibido incluía código fuente, base de datos, logo y resultados
  pesados de PyInstaller (`build` y `dist`).

## Incidencias corregidas

1. La interfaz llamaba al exportador PDF con cinco argumentos, mientras el
   exportador aceptaba cuatro. Esto producía un error al guardar.
2. La pantalla de acceso iniciaba dos ciclos `mainloop` consecutivos.
3. El mensaje de error PDF indicaba incorrectamente que fallaba un EXE.
4. El logo no estaba declarado en `main.spec` para incluirse en el ejecutable.
5. Eliminar un proyecto dejaba partidas APU huérfanas.
6. Las conexiones SQLite no garantizaban rollback ante una excepción.
7. La consulta de proyectos y recursos no tenía orden estable.

## Validaciones ejecutadas

- Compilación sintáctica de todos los archivos Python: correcta.
- Prueba de alta de proyecto, recurso y partida: correcta.
- Cálculo de subtotales y total: correcto.
- Eliminación transaccional de proyecto y partidas: correcta.
- Generación real de PDF con logo: correcta.
- Verificación de datos originales: preservados.

## Riesgo pendiente para el Módulo 2

El acceso actual continúa siendo temporal y está escrito directamente en el
código. El siguiente módulo debe incorporar tablas de usuarios y roles,
contraseñas con hash seguro, usuario administrador inicial, control de sesión y
permisos por pantalla.

## Ampliación de biblioteca APU

Se incorporaron 19 partidas y 161 filas de detalle procedentes del documento
`F. Analisis de Precio Unitarios APU.pdf`. El catálogo maestro ahora contiene
55 recursos. Los precios variables se conservan dentro de cada partida para no
alterar sus costos originales. La nueva pantalla **Biblioteca de Partidas**
permite consultar cada desglose y copiarlo completo a un proyecto.
