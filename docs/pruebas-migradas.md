# Pruebas de la consolidación

Se conservan las pruebas originales de cuentas, autenticación, búsqueda, modelos, catálogo y componentes compatibles. Las pruebas que afirmaban que no se podían guardar imágenes, desactivar productos o registrar pedidos como cajero se actualizaron al contrato consolidado.

Las suites anteriores `pedidos/test.py`, `test_reservas.py` y `test_ventas_insumos.py` se retiraron del proyecto activo y permanecen en las carpetas de las versiones originales. Mezclaban reposición del stock después del reembolso, consumo de ingredientes al cobrar y permisos distintos entre versiones. Su reemplazo ejecutable es `pedidos/test_integracion.py`, que verifica el flujo acordado: crear → preparar → entregar → cobrar. El consumo ocurre al iniciar la preparación, y el reembolso de algo ya preparado no devuelve físicamente ingredientes.

La suite consolidada verifica transacciones de cambio de pedido, reversión completa ante un cambio inválido, reservas compartidas, cobros/reembolsos repetidos, referencia Yape, avisos únicos, fechas locales, permisos, PDFs inmutables y registro de reportes PDF. `test_concurrencia.py` comprueba sobre PostgreSQL dos pedidos simultáneos que comparten el último insumo. En SQLite se omite expresamente porque no ofrece los mismos bloqueos de fila.

`test_rendimiento.py` mide diez registros de pedidos de diez productos y verifica total decimal y duración inferior a cinco segundos. Es una medición dentro del proceso Django, sin latencia de red. El script del navegador añade una medición real del registro desde la interfaz.

RNF1 se mide con `scripts/monitor_disponibilidad.py`, que incluye una consulta a la base de datos. Una comprobación corta no acredita el 99% durante el horario de atención: se deben conservar muestras de jornadas completas. RNF4 se prueba en Chromium a 1440×1000, 768×1024 y 390×844; la conexión desde dispositivos físicos debe validarse en la red de destino.
