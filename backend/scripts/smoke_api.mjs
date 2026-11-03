/**
 * Smoke test del backend de prueba y del contrato que consume el frontend.
 * Uso: node backend/scripts/smoke_api.mjs
 * Requiere el backend en http://localhost:8000 y el frontend en 5173.
 */
import assert from "node:assert/strict";

const API = process.env.API_URL ?? "http://localhost:8000/api";
const WEB = process.env.WEB_URL ?? "http://localhost:5173";
const ORIGEN = new URL(WEB).origin;

async function pedir(ruta, { token, ...opciones } = {}) {
  const res = await fetch(`${API}${ruta}`, {
    ...opciones,
    headers: {
      "Content-Type": "application/json",
      Origin: ORIGEN,
      ...(token && { Authorization: `Bearer ${token}` }),
      ...opciones.headers,
    },
  });
  return res;
}

async function json(ruta, opciones) {
  const res = await pedir(ruta, opciones);
  assert.ok(res.ok, `GET ${ruta} respondió ${res.status}`);
  return res.json();
}

const login = await pedir("/auth/login/", {
  method: "POST",
  body: JSON.stringify({ username: "admin", password: "admin123" }),
});
assert.equal(login.status, 200, "login del administrador");
assert.equal(
  login.headers.get("access-control-allow-origin"),
  ORIGEN,
  "CORS debe permitir el origen de Vite",
);
const sesion = await login.json();
assert.ok(sesion.access, "la respuesta incluye access token");
assert.equal(sesion.rol, "administrador", "la respuesta incluye el rol");

const categorias = await json("/categorias/", { token: sesion.access });
assert.ok(categorias.some((c) => c.nombre === "Bebidas"), "categoría Bebidas");
assert.ok(categorias.some((c) => c.nombre === "Acompañamientos"), "categoría Acompañamientos (UTF-8)");

const productos = await json("/productos/", { token: sesion.access });
assert.ok(productos.length >= 10, "productos sembrados");
assert.equal(typeof productos[0].precio, "string", "precio decimal como string (RNF7)");
assert.ok(productos.some((p) => p.stock === 0), "hay un producto agotado");
assert.ok(productos.some((p) => p.stock > 0 && p.stock <= 5), "hay stock bajo");

const busqueda = await json("/productos/?q=caf", { token: sesion.access });
assert.ok(busqueda.length >= 1, "buscador ILIKE");
assert.ok(busqueda.some((p) => p.nombre === "Café"), "búsqueda con UTF-8");
assert.ok(
  busqueda.every((p) => p.nombre.toLowerCase().includes("caf")),
  "todos los resultados coinciden",
);
assert.equal(busqueda[0].categoria_nombre, "Bebidas", "incluye categoria_nombre");

const pedidos = await json("/pedidos/?estado=ESPERA,EN_PREPARACION,LISTO", {
  token: sesion.access,
});
assert.ok(pedidos.length >= 3, "pedidos para la vista de cocina");
for (const pedido of pedidos) {
  assert.ok(
    ["ESPERA", "EN_PREPARACION", "LISTO"].includes(pedido.estado),
    `estado válido (${pedido.estado})`,
  );
  assert.ok(pedido.detalles.length > 0, "cada pedido trae detalles");
  for (const detalle of pedido.detalles) {
    assert.equal(typeof detalle.producto, "string", "detalle.producto es el nombre");
    assert.equal(typeof detalle.stock, "number", "detalle.stock para StockBadge");
    assert.equal(typeof detalle.cantidad, "number", "detalle.cantidad");
  }
}

const loginMesero = await pedir("/auth/login/", {
  method: "POST",
  body: JSON.stringify({ username: "mesero", password: "mesero123" }),
});
const sesionMesero = await loginMesero.json();
const intentoProducto = await pedir("/productos/", {
  method: "POST",
  token: sesionMesero.access,
  body: JSON.stringify({ nombre: "No permitido", categoria: 1, precio: "1.00", stock: 1 }),
});
assert.equal(intentoProducto.status, 403, "RD1: el mesero no crea productos");

const loginCocina = await pedir("/auth/login/", {
  method: "POST",
  body: JSON.stringify({ username: "cocina", password: "cocina123" }),
});
const sesionCocina = await loginCocina.json();
const saltoInvalido = await pedir("/pedidos/2/estado/", {
  method: "PATCH",
  token: sesionCocina.access,
  body: JSON.stringify({ estado: "LISTO" }),
});
assert.equal(saltoInvalido.status, 400, "RF5: rechaza transición ESPERA → LISTO");

const html = await fetch(WEB).then((r) => r.text());
assert.ok(html.includes('id="root"'), "Vite sirve la aplicación");

console.log("OK: autenticación, CORS, UTF-8, catálogo, buscador, pedidos, permisos y estados.");
