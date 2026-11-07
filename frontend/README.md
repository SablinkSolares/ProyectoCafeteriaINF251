# Interfaz DinoCafé

React con Vite. Usa el estilo compartido de `src/styles.css`, componentes comunes para imágenes, stock y trazabilidad, y `src/api.js` como único cliente de la API.

```powershell
npm ci
npm run dev
npm test
npm run build
```

Requiere Node 22.12+ o Node 24. La aplicación abre en http://localhost:5173. `/api` y `/media` se reenvían a Django. Se puede definir `API_PROXY_TARGET` para otro backend y `VITE_API_URL` para una API externa.

Las rutas de interfaz usan fragmentos, por ejemplo `/#seguimiento` y `/#pedido/12`. Django utiliza IDs enteros en las rutas REST. Los permisos finales siempre los valida el servidor.

El flujo de atención es registrar → preparar → entregar → cobrar. La guía completa está en [README principal](../README.md).
