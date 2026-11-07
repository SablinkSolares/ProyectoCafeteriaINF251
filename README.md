# DinoCafé unificado

Sistema de cafetería con Django REST Framework, React y PostgreSQL/SQLite. Esta es la carpeta de trabajo consolidada. Las versiones de origen se conservaron fuera de ella.

## Iniciar en Windows

Requisitos: Python 3.12 y Node 22.12+ o Node 24.

Desde esta carpeta, en una terminal:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
cd backend
..\.venv\Scripts\python.exe manage.py migrate
..\.venv\Scripts\python.exe manage.py seed_demo
..\.venv\Scripts\python.exe manage.py runserver 0.0.0.0:8000
```

En otra terminal, desde esta carpeta:

```powershell
cd frontend
npm ci
npm run dev
```

Abre **http://localhost:5173**. Vite dirige `/api` y `/media` a Django. SQLite permite probar sin Docker. Los archivos `backend/.env.example` y `frontend/.env.example` son opcionales; cópialos como `.env` en sus respectivas carpetas si quieres cambiar la configuración.

La pantalla inicial muestra una descripción de DinoCafé y el menú público con imágenes, categorías y precios. No requiere cuenta. Para entrar al sistema de gestión utiliza **Acceso del personal**. Desde el panel puedes volver al inicio con **Ver menú**.

Como administrador, abre **Productos → Actualizar stock** en un producto terminado, introduce las unidades disponibles y pulsa **Guardar stock**. Para los productos preparados utiliza **Actualizar insumos**: su disponibilidad depende de las recetas y las existencias de ingredientes.

## Cuentas de demostración

| Usuario | Contraseña | Rol |
|---|---|---|
| admin | admin123 | Administrador |
| mesero | mesero123 | Mesero |
| cajero | cajero123 | Cajero |
| cocina | cocina123 | Cocina |

`seed_demo` crea cuentas si no existen; conserva contraseñas, productos y existencias existentes. Solo genera los pedidos de ejemplo sobre un catálogo nuevo.

## Flujo acordado

**Registrar pedido y mesa → preparar → listo → entregar → cobrar.**

- Mesero, caja y administrador registran pedidos con mesa 1–10 y observaciones.
- Se reservan los productos terminados y los ingredientes de las recetas al registrar.
- Cocina consume los ingredientes al comenzar la preparación. El mesero confirma la entrega.
- Caja cobra después de entregar. Guarda monto recibido, cambio, referencia y responsable.
- Yape QR queda pendiente hasta que caja verifique el ingreso. Al confirmar se genera un aviso de **pago realizado**.
- Una cancelación antes de preparar repone productos y libera ingredientes reservados. Lo preparado no vuelve al inventario.
- Un cambio registra el pedido nuevo y su vínculo con el original. Un pedido ya pagado se reembolsa íntegramente; el reemplazo requiere otro cobro. Si el reemplazo falla, se revierte toda la operación.
- Los productos se desactivan conservando el historial. Los pedidos no se borran.

## Funciones disponibles

- Catálogo con imágenes obligatorias al guardar productos, carga de PNG/JPEG/WebP, búsqueda, categorías, stock exacto y baja lógica.
- Insumos con stock físico, reservado y disponible. Recetas por unidad para productos preparables.
- Cocina, entregas, caja y seguimiento por día con responsables, fechas y detalle por ID.
- Pagos en efectivo y Yape, cambio, reembolsos con motivo y avisos persistentes.
- Ventas por producto, categoría y método. Conciliación diaria separa ventas, reembolsos, neto, monto real y diferencias.
- PDF de ventas y conciliación; historial de PDFs y **reporte de reportes PDF**. Cada documento conserva su contenido original y una huella SHA-256.
- Cuentas y permisos en Django, además de navegación según el rol.

## Configurar Yape

Entra como administrador en **Ajustes**, sube el **QR real de tu cuenta Yape** y guarda. Allí también puedes quitar la imagen o deshabilitar pagos QR.

No hay una conexión bancaria activa ni se confirma un cobro por el mero escaneo. Caja verifica el movimiento en Yape y pulsa **Confirmar pago Yape recibido**. Se preparó un contrato de webhook firmado para un futuro adaptador autorizado; permanece desactivado sin secreto. Detalles en [API](docs/API.md#yape-y-confirmación-de-pagos).

## Organización

```text
DinoCafe/
├── backend/
│   ├── dinocafe/       # Configuración, permisos y salud
│   ├── usuarios/       # Cuentas y JWT
│   ├── catalogo/       # Productos, imágenes, insumos y recetas
│   └── pedidos/        # Flujo, reservas, pagos, avisos y PDF
├── frontend/
│   └── src/
│       ├── components/ # Pantallas y componentes reutilizables
│       ├── api.js      # Cliente HTTP y sesión
│       ├── utils.js    # Fechas, estados y moneda
│       └── styles.css  # Estilo compartido y adaptable
├── scripts/            # Verificación y disponibilidad
├── docs/               # Requisitos, integración y evidencias
└── docker-compose.yml
```

## Docker y PostgreSQL

Para el entorno de desarrollo completo, detén primero los procesos locales que usen 8000 o 5173:

```powershell
docker compose up --build
```

La base de datos queda en una red interna. Los volúmenes conservan PostgreSQL y las imágenes subidas. La configuración es para desarrollo; el despliegue definitivo debe utilizar su propia configuración y servidor de aplicaciones.

## Verificación

```powershell
.\.venv\Scripts\python.exe scripts\verificar_backend.py
cd frontend
npm test
npm run build
```

La prueba de concurrencia se ejecuta con PostgreSQL; se omite en SQLite. Para los recorridos de navegador:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m playwright install chromium
.\.venv\Scripts\python.exe scripts\verificar_navegador.py
```

Este último script crea **una venta de prueba local y PDFs**, usando las cuentas demo. No se debe ejecutar sobre datos reales. Guarda capturas y resultados en `docs/evidencias/`.

Consulta [estado de requisitos](docs/REQUISITOS.md), [API y reglas](docs/API.md), [orígenes](docs/CONSOLIDACION.md) y [pruebas migradas](docs/pruebas-migradas.md).

También se incluyen un [informe de implementación en PDF](docs/INFORME_IMPLEMENTACION.pdf), un [PDF de ventas de ejemplo](docs/evidencias/ventas-ejemplo.pdf) y un [PDF del historial de reportes](docs/evidencias/historial-reportes-ejemplo.pdf), todos con datos de demostración.
