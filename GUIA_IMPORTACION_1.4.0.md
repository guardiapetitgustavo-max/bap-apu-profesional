# Guía de importación de recursos y precios

## Descargar la plantilla

Abra `Recursos`, ingrese en `Importar Excel / CSV` y seleccione `Descargar plantilla Excel`.
También puede guardar la hoja `Importacion` como CSV delimitado por coma o punto y coma.

## Columnas obligatorias

- `Nombre_Recurso`
- `Unidad`
- `Tipo`
- `Precio`

El tipo debe ser `Material`, `Mano de Obra` o `Equipo`. El precio debe ser mayor a cero.

## Reconocimiento de recursos

El sistema busca primero `Codigo_Recurso`. Si está vacío, compara `Nombre_Recurso` y `Unidad`.
Use códigos permanentes para evitar duplicados cuando distintas empresas escriben una misma
descripción de maneras diferentes.

## Registrar tres proveedores

Repita el mismo código y recurso en tres filas. Cambie el RUC, nombre, precio, calidad, stock,
entrega y fuente en cada fila. El sistema creará un solo recurso y tres ofertas comparables.

## Actualizar el catálogo

- `Actualizar_Precio = NO`: registra la oferta sin cambiar el precio principal.
- `Actualizar_Precio = SI`: actualiza el precio principal y conserva el valor anterior.

Revise siempre la vista previa. Las filas incorrectas se muestran con su observación y se omiten.
La operación confirmada se registra en la auditoría.

## Elegir una oferta

Abra `Comparar proveedores`, seleccione un recurso y revise precio, marca, calidad, stock,
plazo y fecha. Pulse `Usar` en la oferta elegida. Esta decisión actualiza el precio vigente sin
modificar los APU ya guardados; los APU nuevos usarán el precio actualizado.
