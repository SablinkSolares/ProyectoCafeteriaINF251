# Requisitos y verificación

| Solicitud | Resultado |
|---|---|
| Inicio público | Descripción breve y menú de productos activos con precios e imágenes, sin exigir sesión ni mostrar datos internos |
| Edición rápida de stock | Administración puede actualizar unidades de terminados desde el catálogo; preparables enlazan a insumos |
| Unir versiones y ordenar el proyecto | Aplicación única en backend/frontend; orígenes preservados y manifestados |
| Unificar estilos | Estilo compartido para todas las áreas, adaptado a escritorio, tablet y celular |
| Generar reportes PDF | Ventas por período y conciliación diaria, con descarga autenticada |
| Reporte de reportes PDF | Historial por fecha de emisión y exportación del historial a PDF |
| Mostrar stock disponible | Cantidad explícita; en preparables depende de los ingredientes libres |
| Insumos para preparables | Gestión de insumos y recetas por unidad en formulario de producto |
| Exigir imagen de producto | Validación de imagen, carga de archivos y vista previa |
| Revisar atributos del pedido | Mesa, observaciones, responsables, fechas, precio aplicado y relación original/reemplazo |
| Django con ID en URL | Convertidores enteros en rutas de recursos y PDF; detalle de pedido enlazable |
| Seguimiento por día | Filtro en API y pantalla con zona America/La_Paz |
| Notificar pagos | Avisos persistentes de pagos confirmados, con sondeo cada cuatro segundos |
| Pago por QR / Yape | Imagen configurable, referencia y confirmación verificada por caja |
| Confirmación automática al escanear | Pendiente de acceso a un mecanismo autorizado del proveedor; un escaneo no confirma recepción de dinero |
| Quitar QR opcionalmente | Administración puede quitar la imagen o deshabilitar el método |
| RF8/RD2 cambio de pedido | Original/reemplazo, motivo, reembolso si corresponde y reversión atómica si falla |
| RF7 conciliación | Efectivo/Yape: bruto, reembolsos, neto, recibido real y diferencias |
| RNF3 permisos por rol | Controles de lectura y escritura en API y navegación según rol |
| RNF2 registro <5 segundos | Medición repetida dentro de Django y recorrido real de navegador |
| RNF4 dispositivos | Chromium a 1440×1000, 768×1024 y 390×844; falta prueba en dispositivos físicos de la red destino |
| RNF1 disponibilidad 99% | Monitor preparado; una muestra breve no acredita el requisito de jornadas completas |

Las pruebas ejecutadas y capturas se guardan en `evidencias/` y los logs de backend. Los PDF de ejemplo usan datos de demostración.

## Permisos adoptados

| Operación | Administrador | Mesero | Cajero | Cocina |
|---|---|---|---|---|
| Consultar productos activos | Sí | Sí | Sí | Sí |
| Crear/editar/desactivar productos y recetas | Sí | No | No | No |
| Gestionar insumos y configurar QR | Sí | No | No | No |
| Registrar pedido | Sí | Sí | Sí | No |
| Consultar historial completo de pedidos | Sí | No | Sí | No |
| Consultar pedidos activos | Sí | Sí | Sí | Sí |
| Iniciar preparación / marcar listo | Sí | No | No | Sí |
| Confirmar entrega | Sí | Sí | No | No |
| Cancelar antes de entregar | Sí | Sí | Sí | No |
| Cambiar pedido y relacionar reemplazo | Sí | No | Sí | No |
| Cobrar, confirmar Yape y reembolsar | Sí | No | Sí | No |
| Consultar ventas y conciliar | Cualquier período | No | Día actual | No |
| Generar/descargar PDF | Todos | No | Propios del día actual | No |
| Reporte PDF del historial de reportes | Sí | No | No | No |
| Crear cuentas | Sí | No | No | No |

Los avisos de pagos se muestran a caja/administración. Los avisos de pedidos listos también están disponibles para el personal operativo.

## Disponibilidad y acceso por red

Para registrar una jornada de ocho horas con una muestra por minuto:

```powershell
.\.venv\Scripts\python.exe scripts\monitor_disponibilidad.py --muestras 480 --intervalo 60 --salida docs\disponibilidad-jornada.json
```

El endpoint de salud consulta también la base. Registra jornadas completas y conserva las interrupciones; no se puede inferir disponibilidad mensual desde diez muestras.

Para un teléfono o tablet en la misma red, abre `http://IP-DEL-EQUIPO:5173`. Vite y Django escuchan en 0.0.0.0 y el proxy usa rutas relativas, así que el teléfono no intenta conectarse a su propio localhost. Si personalizas `DJANGO_ALLOWED_HOSTS`, incluye esa IP. La prueba física queda condicionada a la red y a las reglas de firewall del equipo.
