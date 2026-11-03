# DinoCafé — entorno de prueba para el frontend

Estructura de prueba para que la **capa de presentación** (React + Vite) corra
contra un backend real de Django con base de datos y datos de demostración.
El trabajo está centrado en las tareas de **Carlos Quispe**:

| Sprint | Tarea | Requisito | Archivos principales |
|---|---|---|---|
| 1 | S1-T04 | RF1 | `Catalogo.jsx`, `ProductoForm.jsx` |
| 1 | S1-T08 | RF3/RF5 | `VistaCocina.jsx` |
| 2 | S2-T02 | RF4 | `StockBadge.jsx` (integrado en catálogo y cocina) |
| 2 | S2-T08 | RF9 | `BuscadorProductos.jsx` |

> El acceso con usuario y contraseña es **provisional, solo para pruebas**.
> La pantalla definitiva de login y las rutas protegidas son S1-T02 (Noemi).

## Estructura

```
proy_ing/
├── frontend/dinocafe-frontend/   # React + Vite (puerto 5173)
├── backend/                      # Django + DRF + JWT (puerto 8000)
│   ├── dinocafe/                 # configuración del proyecto
│   ├── usuarios/                 # usuarios, roles y login JWT (RF10/RNF3)
│   ├── catalogo/                 # categorías y productos (RF1/RF4/RF9)
│   ├── pedidos/                  # pedidos, detalle y estados (RF2/RF3/RF5)
│   └── usuarios/management/commands/seed_demo.py  # datos de demostración
├── docker-compose.yml            # PostgreSQL + Django + React
└── README.md
```

## Opción A — Local rápido (SQLite, sin Docker)

Requisitos: **Python 3.12+** y **Node 20+**.

### 1. Backend

```powershell
cd backend
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe manage.py migrate
.venv\Scripts\python.exe manage.py seed_demo
.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000
```

La API queda en `http://localhost:8000/api/`. Por defecto usa SQLite
(`backend/db.sqlite3`), así que no hace falta instalar PostgreSQL para probar.
Puedes comprobar que está arriba en `http://localhost:8000/api/health/`.

### 2. Frontend

En otra terminal:

```powershell
cd frontend\dinocafe-frontend
npm install
copy .env.example .env
npm run dev
```

Abrir **http://localhost:5173**.

## Opción B — Docker (PostgreSQL + Django + React)

```powershell
docker compose up --build
```

- Frontend: http://localhost:5173
- API: http://localhost:8000/api/
- Salud del backend: http://localhost:8000/api/health/
- PostgreSQL: `localhost:5432` (`dinocafe` / `dinocafe` / `dinocafe`)

El contenedor del backend aplica migraciones y ejecuta `seed_demo` al arrancar.

## Cuentas de prueba

| Usuario | Contraseña | Rol | Qué ve |
|---|---|---|---|
| `admin` | `admin123` | administrador | Catálogo (con alta/edición) y Cocina |
| `mesero` | `mesero123` | mesero | Catálogo en modo consulta |
| `cajero` | `cajero123` | cajero | Catálogo en modo consulta |
| `cocina` | `cocina123` | cocina | Catálogo y Cocina |

La pantalla de acceso trae botones para completar cada cuenta.

## Datos de demostración

- **Categorías:** Bebidas y Acompañamientos.
- **10 productos** con precios decimales y stocks variados (incluye stock bajo y agotado).
- **5 pedidos**: 2 en espera, 1 en preparación, 1 listo y 1 entregado.
- Los pedidos se crean solo si la tabla está vacía; los usuarios y productos se
  actualizan al volver a ejecutar `seed_demo`. Para volver a dejar los pedidos en
  sus estados iniciales usa `python manage.py seed_demo --reset-pedidos`.

## Endpoints que usa el frontend

| Método | Ruta | Uso |
|---|---|---|
| GET | `/api/health/` | Comprobar que el backend está arriba |
| POST | `/api/auth/login/` | Devuelve `access`, `refresh`, `rol`, `username` |
| GET | `/api/categorias/` | Categorías |
| GET | `/api/productos/?q=&categoria=` | Catálogo y buscador (ILIKE) |
| POST | `/api/productos/` | Crear producto (solo administrador) |
| PATCH | `/api/productos/{id}/` | Editar producto (solo administrador) |
| GET | `/api/pedidos/?estado=ESPERA,EN_PREPARACION,LISTO` | Vista de cocina |
| POST | `/api/pedidos/` | Registrar pedido (mesero/administrador) |
| PATCH | `/api/pedidos/{id}/estado/` | Cambiar estado según la máquina de estados |

Reglas de la prueba:

- Solo el administrador crea o edita productos (RD1).
- La cocina avanza `ESPERA → EN_PREPARACION → LISTO`.
- El mesero registra la entrega `LISTO → ENTREGADO`.
- Las transiciones inválidas responden `400` y los permisos denegados `403`.

## Cómo probar la parte de Carlos

1. Entrar como `admin` y abrir **Catálogo** (S1-T04): alta, edición, filtro por
   categoría y validación de precio/stock.
2. Escribir en el buscador (S2-T08): filtra por coincidencia y muestra el
   resultado; `Escape` o “Limpiar” restablece la lista.
3. Observar las etiquetas de stock (S2-T02): `Disponible`, `Quedan N` y
   `Agotado` (probar con “Cocoa”, “Trozo de torta” y “Cocoa con leche”).
4. Abrir **Cocina** (S1-T08): pedidos en columnas, orden de llegada, stock de
   cada línea y botones para avanzar el estado.
5. Cambiar de rol con **Salir** y repetir el recorrido como `cocina` o `mesero`.

### Pruebas automáticas

```powershell
# Contrato del backend (requiere backend y frontend arriba)
cd backend
node scripts/smoke_api.mjs

# Componentes de Carlos (Vitest + Testing Library)
cd ..\frontend\dinocafe-frontend
npm test
```

El smoke test comprueba autenticación, CORS, UTF-8, catálogo, buscador, pedidos,
permisos y transiciones. La suite del frontend cubre stock, formulario,
buscador, catálogo y vista de cocina (17 pruebas).

## Notas

- Para usar PostgreSQL local sin Docker: define `DB_ENGINE=postgres` y las
  variables `POSTGRES_*` (ver `backend/.env.example`).
- Las contraseñas y la `SECRET_KEY` son de prueba; no usar en producción.
- El backend de esta carpeta es un **mock funcional** para integrar el frontend,
  no el backend definitivo del equipo. Sigue el contrato acordado en el README
  del frontend.
