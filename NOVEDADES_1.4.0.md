# BAP APU Profesional 1.4.0

## Importación empresarial

- Admite archivos Excel `.xlsx` y CSV delimitados por coma o punto y coma.
- Permite crear recursos y actualizar precios existentes.
- Reconoce recursos por código y, como alternativa, por nombre más unidad.
- Valida campos, números, RUC, fechas, tipo, calidad, stock y plazo de entrega.
- Muestra una vista previa y omite filas inválidas antes de confirmar.
- Registra cada importación en la auditoría.

## Proveedores y comparación

- Registra proveedores nuevos a partir de sus listas de precios.
- Mantiene varias ofertas por recurso.
- Compara precio, marca, calidad, stock, entrega y fecha.
- Permite elegir una oferta para actualizar el precio vigente.
- Conserva el historial de cambios de precio.
- Exporta ofertas e historial en el reporte Excel general.

## Regla de seguridad

La columna `Actualizar_Precio` controla los cambios. `NO` registra la oferta sin modificar
el catálogo principal. `SI` actualiza el precio del recurso y guarda el valor anterior.
