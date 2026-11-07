/** Comprobación HTTP de lectura del entorno demo; no crea ventas. */
import assert from "node:assert/strict";
const API = process.env.API_URL || "http://localhost:8000/api";
async function pedir(ruta, token, opciones={}) {
  return fetch(`${API}${ruta}`,{...opciones,headers:{"Content-Type":"application/json",...(token && {Authorization:`Bearer ${token}`}),...opciones.headers}});
}
async function login(username) {
  const res=await pedir("/auth/login/",null,{method:"POST",body:JSON.stringify({username,password:`${username}123`})});
  assert.equal(res.status,200,`login ${username}`);
  return (await res.json()).access;
}
assert.equal((await pedir("/health/")).status,200);
const menu=await pedir("/menu/");
assert.equal(menu.status,200);
const menuPublico=await menu.json();
assert.ok(Array.isArray(menuPublico.productos));
assert.ok(menuPublico.productos.every(p=>!("stock" in p) && !("insumos" in p)));
assert.equal((await pedir("/productos/")).status,401);
const admin=await login("admin");
const perfil=await (await pedir("/auth/me/",admin)).json();
assert.equal(perfil.rol,"administrador");
const pagina=await (await pedir("/productos/",admin)).json();
const productos=Array.isArray(pagina)?pagina:pagina.results;
assert.ok(productos.length>0);
assert.equal(typeof productos[0].precio,"string");
assert.equal(typeof productos[0].stock_disponible,"number");
assert.equal((await pedir("/insumos/",admin)).status,200);
assert.equal((await pedir("/reportes/",admin)).status,200);
const mesero=await login("mesero");
assert.equal((await pedir("/pagos/",mesero)).status,403);
assert.equal((await pedir("/usuarios/",mesero)).status,403);
const cocina=await login("cocina");
assert.equal((await pedir("/pedidos/",cocina,{method:"POST",body:"{}"})).status,403);
const cajero=await login("cajero");
assert.equal((await pedir("/reportes/?desde=2020-01-01&hasta=2020-01-01",cajero)).status,403);
console.log("API: salud, sesión, catálogo, inventario, reportes y permisos correctos.");
