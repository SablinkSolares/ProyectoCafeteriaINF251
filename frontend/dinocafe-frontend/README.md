# DinoCafé – Capa de presentación (tareas de Carlos Quispe)

React + Vite. Cubre: S1-T04 (catálogo, RF1), S1-T08 (vista de cocina, RF3/RF5),
S2-T02 (indicadores de stock, RF4), S2-T08 (buscador, RF9).

## Ejecutar

Necesita el backend de prueba de `../../backend` en el puerto 8000.

```powershell
npm install
copy .env.example .env
npm run dev
```

Abrir http://localhost:5173. La pantalla de acceso es **provisional** (S1-T02 la
reemplaza); permite entrar con las cuentas de prueba:

| Usuario | Contraseña | Rol |
|---|---|---|
| `admin` | `admin123` | administrador |
| `mesero` | `mesero123` | mesero |
| `cajero` | `cajero123` | cajero |
| `cocina` | `cocina123` | cocina |

El token JWT y el rol se guardan en `localStorage` como `access_token` y `rol`.
El botón **Salir** los elimina.

## Pruebas

```powershell
npm test          # una vez
npm run test:watch
```

Cubren S1-T04 (formulario y catálogo), S1-T08 (vista de cocina), S2-T02
(indicadores de stock) y S2-T08 (buscador). Usan Vitest, jsdom y Testing Library.

## Contrato de API que esta interfaz espera

| Método | Ruta | Respuesta / cuerpo |
|---|---|---|
| POST | `/auth/login/` | `{access, refresh, rol, username}` |
| GET | `/categorias/` | `[{id, nombre}]` |
| GET | `/productos/?q=&categoria=` | `[{id, nombre, categoria, categoria_nombre, precio:"7.50", stock}]` (q = ILIKE) |
| POST / PATCH | `/productos/`, `/productos/{id}/` | `{nombre, categoria, precio, stock}` |
| GET | `/pedidos/?estado=ESPERA,EN_PREPARACION,LISTO` | `[{id, estado, creado_en, detalles:[{id, producto, cantidad, stock}]}]` |
| POST | `/pedidos/` | `{detalles:[{producto, cantidad}]}` (mesero/administrador) |
| PATCH | `/pedidos/{id}/estado/` | `{estado}` – el servidor valida la transición y el rol |

Estados: ESPERA, EN_PREPARACION, LISTO, ENTREGADO. Precios como string decimal (RNF7).
Umbral de stock bajo: `STOCK_BAJO` en `components/StockBadge.jsx`. `StockBadge` se reutiliza en la vista del mesero (S1-T06).

## Archivos de esta entrega

- `components/Catalogo.jsx` – consulta, filtro por categoría, avisos y acceso a alta/edición (S1-T04).
- `components/ProductoForm.jsx` – formulario con validación decimal y de stock (S1-T04).
- `components/VistaCocina.jsx` – columnas por estado, sondeo cada 5 s y cambio de estado (S1-T08).
- `components/StockBadge.jsx` – indicador reutilizable de disponibilidad (S2-T02).
- `components/BuscadorProductos.jsx` – búsqueda con retardo de 300 ms y limpieza (S2-T08).
- `components/LoginDev.jsx` – acceso provisional para probar (no es S1-T02).
