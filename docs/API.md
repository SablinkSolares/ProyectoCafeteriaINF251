# API y reglas

Todas las rutas salvo el menú público, salud, login y el contrato de webhook requieren JWT. Inicio: `POST /api/auth/login/`, renovación: `POST /api/auth/refresh/`, perfil validado en servidor: `GET /api/auth/me/`.

## Recursos

| Ruta | Operaciones |
|---|---|
| /api/menu/ | GET público: productos activos con imagen, categoría y precio; sin stock ni recetas |
| /api/categorias/ | GET |
| /api/productos/ | GET paginado, POST |
| /api/productos/{id}/ | GET, PATCH, DELETE como baja lógica |
| /api/productos/{id}/stock/ | PATCH exclusivo de administración: stock y stock_anterior opcional; solo productos terminados |
| /api/imagenes/ | POST multipart, campo imagen; PNG/JPEG/WebP, hasta 5 MB |
| /api/insumos/ | GET, POST |
| /api/insumos/{id}/ | GET, PATCH |
| /api/configuracion-pago/ | GET; PATCH exclusivo de administración |
| /api/pedidos/ | GET con estado y fecha; POST con mesa, observaciones y detalles |
| /api/pedidos/{id}/ | GET; no permite edición arbitraria ni eliminación |
| /api/pedidos/{id}/estado/ | PATCH estado |
| /api/pedidos/{id}/cancelar/ | POST motivo |
| /api/pedidos/{id}/cambiar/ | POST motivo, mesa, observaciones y detalles nuevos |
| /api/pagos/ | GET, POST |
| /api/pagos/{id}/confirmar/ | POST |
| /api/pagos/{id}/reembolsar/ | POST motivo; importe total |
| /api/pagos/reporte-ventas/?desde=YYYY-MM-DD&hasta=YYYY-MM-DD | GET |
| /api/pagos/conciliacion/ | POST fecha, efectivo_real, qr_real |
| /api/notificaciones/?despues={id} | GET avisos nuevos |
| /api/reportes/?desde=YYYY-MM-DD&hasta=YYYY-MM-DD | GET por fecha de emisión |
| /api/reportes/ | POST tipo VENTAS, CONCILIACION o HISTORIAL |
| /api/reportes/{id}/pdf/ | GET descarga del documento original |
| /api/usuarios/ | GET, POST exclusivo de administración |
| /api/health/ | GET API y conexión con base de datos |

Ejemplo de pedido:

```json
{"mesa": 3, "observaciones": "Sin azúcar", "detalles": [{"producto": 2, "cantidad": 1}]}
```

El precio lo determina Django. Las cantidades repetidas se agrupan. Las operaciones sobre inventario usan transacciones y bloqueos de fila en PostgreSQL. Los preparables requieren receta; las reservas se consumen al comenzar la preparación, no al pagar.

Ejemplo de alta de producto preparable:

```json
{"nombre": "Café con leche", "categoria": 1, "precio": "9.50", "preparable": true, "imagen": "/media/productos/archivo.png", "insumos": [{"insumo": 1, "cantidad_insumo_por_unidad": "10.000"}, {"insumo": 2, "cantidad_insumo_por_unidad": "200.000"}]}
```

Las unidades deben ser las del insumo registrado. El administrador puede ajustar existencias, pero no por debajo de las reservas activas.

Para la edición rápida del stock de un producto terminado se envía `{"stock": 20, "stock_anterior": 12}` a `/api/productos/{id}/stock/`. El stock representa las unidades disponibles para pedidos nuevos y debe ser entero y no negativo. La operación bloquea el producto durante la actualización; si se envía `stock_anterior` y ya cambió, responde 409 para evitar sobrescribir reservas o ediciones recientes. Los preparables se gestionan a través de sus insumos y no admiten este ajuste directo.

## Yape y confirmación de pagos

`metodo=QR` representa Yape Bolivia en esta versión; `metodo=EFECTIVO` representa efectivo. El total viaja como decimal textual. Los pagos en efectivo admiten un monto recibido mayor y guardan el cambio. Yape requiere importe exacto y referencia.

El QR real se carga desde Ajustes. **No hay conexión activa con Yape**: caja debe verificar el movimiento en su cuenta y confirmar. El aviso de pago se emite una sola vez. La guía pública de [transferencias QR de Yape Bolivia](https://www.yape.com.bo/centro_de_ayuda/enviar-y-recibir-yapeos/como-realizo-una-transferencia-por-QR/) describe el pago desde su aplicación; no se utiliza esa página como si fuera una API de confirmación.

Se dejó `POST /api/pagos/webhook-qr/` como contrato interno para un futuro adaptador autorizado. **No es una API pública de Yape ni está conectado a ella**. Sin `QR_WEBHOOK_SECRET` responde 503. Con un adaptador real, el cuerpo exacto se firma con HMAC-SHA256 y la firma hexadecimal se envía en `X-QR-Signature`:

```json
{"evento": "identificador-unico", "pago_id": 12, "monto": "7.00", "estado": "COMPLETADO", "referencia_qr": "referencia-real"}
```

Valida firma, importe, referencia, método y pedido entregado; conserva un identificador único y tolera reintentos. El adaptador debe obtener los eventos del proveedor mediante acceso autorizado. No se inventa un cobro exitoso al abrir una imagen o escanear un código.

## Reportes

Ventas y reembolsos se contabilizan en sus respectivas fechas locales. Por eso un día puede tener neto negativo si solo hubo devoluciones de ventas anteriores. Los desgloses de productos/categorías muestran bruto y nombres actuales; esa convención se imprime también en el PDF.

Para emitir ventas:

```json
{"tipo": "VENTAS", "desde": "2026-11-06", "hasta": "2026-11-06"}
```

Para conciliación:

```json
{"tipo": "CONCILIACION", "fecha": "2026-11-06", "efectivo_real": "50.00", "qr_real": "20.00"}
```

Para el reporte de reportes emitidos:

```json
{"tipo": "HISTORIAL", "desde": "2026-11-06", "hasta": "2026-11-06"}
```

La respuesta 201 contiene ID, tipo, autor, período, fecha, resumen, SHA-256 y URL. La descarga exige el mismo control de permisos; no hay archivos públicos. El documento histórico conserva los bytes originales aunque luego cambien productos, ventas o devoluciones.

Los IDs se validan con los [convertidores de rutas de Django](https://docs.djangoproject.com/en/5.1/topics/http/urls/). Las tablas PDF permiten varias páginas y repiten su encabezado mediante [ReportLab](https://docs.reportlab.com/reportlab/userguide/ch7_tables/).
