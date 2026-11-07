# Orígenes y decisiones de consolidación

Se creó una nueva carpeta `DinoCafe` como único proyecto activo. El usuario confirmó expresamente eliminar `ProyectoCafeteriaINF251-dorian`, `ProyectoCafeteriaINF251-full` y `versiones-originales`, pero la política de ejecución bloqueó el borrado. Esas tres carpetas permanecen en el directorio principal y pueden retirarse manualmente desde el Explorador; no falta autorización del usuario. En la limpieza posterior se eliminaron los ZIP opcionales tras verificar que las fuentes originales extraídas seguían completas. Las rutas de `fuentes.json` corresponden al directorio `versiones-originales/`; sus 311 archivos de origen se verificaron sin diferencias.

| Fuente | Aporte |
|---|---|
| ProyectoCafeteriaINF251-dorian | Base de aplicaciones Django, cuentas, reservas de insumos, reportes, filtros y pruebas |
| ProyectoCafeteriaINF251-full | Contrato inicial de catálogo, cocina, stock y pruebas de componentes |
| ProyectoCafeteriaINF251-main | Carpeta sin archivos en la revisión |
| DinoCafe_Catalogo_Imagenes_BajaLogica (2)/…/DinoCafe-Frontend-main | Imágenes, baja lógica, mesas, responsables y fechas de atención |
| models.py de la carpeta original | Separación de existencias, insumos y recetas, ya incorporada en la base |
| dino/dino | Recursos gráficos proporcionados, conservados como material de marca |

`fuentes.json` registra rutas y huellas de los archivos de las cuatro carpetas de código. Se mantuvo una sola aplicación React y una sola API; las funcionalidades se integraron sobre las migraciones de `dorian` para no mezclar dos historiales incompatibles.

El frontend está directamente en `frontend/`, sin otra carpeta anidada con el mismo propósito. Las pantallas comparten colores, tipografía, formularios, tarjetas, tablas y comportamiento adaptable. Los archivos de pruebas viven junto a los módulos que verifican. Los servicios de stock/pagos y de reportes se separan en `pedidos/insumos.py`, `services.py` y `reporting.py`.

Se resolvió el conflicto entre cobro previo y posterior a cocina siguiendo la decisión del usuario: **cobro después de entregar**. Se conservan mesas y responsables de la otra versión, pero no su requisito de pago anticipado.

Los preparables calculan disponibilidad desde ingredientes y recetas. Los terminados usan existencias en unidades. Las líneas de pedido guardan precio aplicado y tipo de producto para que un cambio posterior del catálogo no altere el consumo histórico. Las reservas de insumos conservan la receta aplicada en el registro del pedido.

No se mezclaron automáticamente bases de datos de versiones distintas. El entorno entregado usa una base local de demostración. Para reutilizar una base existente, respalda los datos, confirma que su historial corresponde a `dorian` y ejecuta las migraciones nuevas sobre una copia. Una base de la versión de imágenes tiene otro historial: se deben exportar e importar registros y mapear IDs, nunca copiar una base encima de otra. Los registros históricos sin responsables o reservas se muestran como tales; no se inventan movimientos de inventario.

Los PDF son archivos inmutables almacenados en la base de datos junto a período, autor, fecha y SHA-256. El historial puede producir a su vez un PDF de los reportes emitidos, sin sumar nuevamente sus ventas ni contarlas como nuevas operaciones.
