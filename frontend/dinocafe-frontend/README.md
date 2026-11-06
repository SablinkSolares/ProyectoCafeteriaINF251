# DinoCafé — frontend React + Vite

Interfaz de catálogo público y operación interna de la cafetería. Conserva React 18, Vite 5 y la hoja de estilos del proyecto original.

## Vistas

- **Portada:** muestra las imágenes del carrusel; el catálogo real requiere iniciar sesión porque la API actual no permite lectura anónima.
- **Catálogo:** consulta de productos, categorías y disponibilidad con la API existente. Las imágenes incluidas se asocian por nombre en el frontend; el servidor aún no guarda rutas de imagen ni baja lógica.
- **Pedidos y caja:** el mesero o administrador registra el pedido; el administrador o cajero registra los pagos. La selección de mesas está visible, pero deshabilitada porque la API actual no guarda ese dato.
- **Cocina:** consulta pedidos por estado y los marca en preparación y listo; la API actual no restringe la lista a pagos verificados.
- **Entregas:** el mesero recibe avisos de pedidos listos y solo confirma la entrega.
- **Seguimiento:** administración consulta pedidos y pagos; las mesas, responsables y fechas por estado no están disponibles en la API actual.
- **Ventas y usuarios:** está conectada la conciliación diaria. El reporte por periodo y producto y la gestión de usuarios permanecen visibles como no disponibles.

## Ejecutar

El backend Django debe estar levantado en `http://localhost:8000`.

```powershell
npm install
copy .env.example .env
npm run dev
```

Abre `http://localhost:5173`.

## QR empresarial

Coloca el archivo real de la empresa en `public/qr-empresa.png`. Si no existe, la pantalla de caja muestra un espacio de reemplazo. La verificación del QR es manual; esta aplicación no se conecta a un banco.

## Cuentas de demostración

| Usuario | Contraseña | Rol |
|---|---|---|
| admin | admin123 | administrador |
| cajero | cajero123 | cajero |
| cocina | cocina123 | cocina |
| mesero | mesero123 | mesero |

## Pruebas

```powershell
npm test
npm run build
```

La API REST se centraliza en `src/api.js`; los componentes mantienen la presentación y las reglas de interfaz en `src/components/`. Los estilos se conservan en `src/styles.css`.
