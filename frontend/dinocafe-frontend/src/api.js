// Capa de presentación: único punto de contacto con la API REST de Django (RNF5).
// El token JWT y el rol los guarda la pantalla de login (S1-T02, Noemi).
const BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8000/api";

export const getToken = () => localStorage.getItem("access_token");
export const getRol = () => localStorage.getItem("rol"); // administrador | mesero | cajero | cocina

export function guardarSesion({ access, rol }) {
  localStorage.setItem("access_token", access);
  localStorage.setItem("rol", rol);
}

export function cerrarSesion() {
  localStorage.removeItem("access_token");
  localStorage.removeItem("rol");
}

async function request(path, options = {}) {
  const token = getToken();
  const res = await fetch(`${BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token && { Authorization: `Bearer ${token}` }),
      ...options.headers,
    },
  });
  if (!res.ok) {
    let detalle = "";
    try {
      const d = await res.json();
      detalle = d.detail || Object.values(d).flat().join(" ");
    } catch { /* respuesta sin cuerpo JSON */ }
    throw new Error(detalle || `Error ${res.status}`);
  }
  return res.status === 204 ? null : res.json();
}

// Autenticación provisional para pruebas (la pantalla definitiva es S1-T02, Noemi).
export const authApi = {
  login: (username, password) =>
    request("/auth/login/", { method: "POST", body: JSON.stringify({ username, password }) }),
};

// Los precios viajan como string decimal ("12.50") para no perder exactitud (RNF7).
export const productosApi = {
  listar: ({ q = "", categoria = "" } = {}) =>
    request(`/productos/?${new URLSearchParams({ q, categoria })}`),
  categorias: () => request("/categorias/"),
  crear: (datos) => request("/productos/", { method: "POST", body: JSON.stringify(datos) }),
  actualizar: (id, datos) =>
    request(`/productos/${id}/`, { method: "PATCH", body: JSON.stringify(datos) }),
};

export const pedidosApi = {
  listarCocina: () => request("/pedidos/?estado=ESPERA,EN_PREPARACION,LISTO"),
  cambiarEstado: (id, estado) =>
    request(`/pedidos/${id}/estado/`, { method: "PATCH", body: JSON.stringify({ estado }) }),
};
