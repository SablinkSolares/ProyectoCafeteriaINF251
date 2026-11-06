// Capa de presentación: único punto de contacto con la API REST de Django (RNF5).
const BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8000/api";

export const getToken = () => localStorage.getItem("access_token");
export const getRefreshToken = () => localStorage.getItem("refresh_token");
export const getRol = () => localStorage.getItem("rol");
export const getUsuario = () => localStorage.getItem("username");

export function guardarSesion({ access, refresh, rol, username }) {
  localStorage.setItem("access_token", access);
  if (refresh) localStorage.setItem("refresh_token", refresh);
  localStorage.setItem("rol", rol);
  if (username) localStorage.setItem("username", username);
}

export function cerrarSesion() {
  localStorage.removeItem("access_token");
  localStorage.removeItem("refresh_token");
  localStorage.removeItem("rol");
  localStorage.removeItem("username");
}

let refreshEnCurso;

async function renovarSesion() {
  const refresh = getRefreshToken();
  if (!refresh) {
    cerrarSesion();
    const error = new Error("La sesión expiró. Ingresa de nuevo.");
    error.status = 401;
    throw error;
  }
  if (!refreshEnCurso) {
    refreshEnCurso = fetch(`${BASE}/auth/refresh/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh }),
    }).then(async (res) => {
      if (!res.ok) {
        cerrarSesion();
        const error = new Error("La sesión expiró. Ingresa de nuevo.");
        error.status = 401;
        throw error;
      }
      const datos = await res.json();
      if (!datos.access) {
        cerrarSesion();
        throw new Error("El servidor no pudo renovar la sesión.");
      }
      localStorage.setItem("access_token", datos.access);
      if (datos.refresh) localStorage.setItem("refresh_token", datos.refresh);
      return datos.access;
    }).finally(() => {
      refreshEnCurso = null;
    });
  }
  return refreshEnCurso;
}

async function request(path, options = {}, reintentar = true) {
  const enviar = (token) => fetch(`${BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token && { Authorization: `Bearer ${token}` }),
      ...options.headers,
    },
  });
  const esAcceso = path === "/auth/login/" || path === "/auth/refresh/";
  let res = await enviar(esAcceso ? null : getToken());
  if (res.status === 401 && reintentar && !["/auth/login/", "/auth/refresh/"].includes(path)) {
    res = await enviar(await renovarSesion());
  }
  if (!res.ok) {
    let detalle = "";
    try {
      const d = await res.json();
      detalle = d.detail || Object.values(d).flat().join(" ");
    } catch { /* respuesta sin cuerpo JSON */ }
    const error = new Error(detalle || `Error ${res.status}`);
    error.status = res.status;
    throw error;
  }
  return res.status === 204 ? null : res.json();
}

export const authApi = {
  login: (username, password) =>
    request("/auth/login/", { method: "POST", body: JSON.stringify({ username, password }) }),
  // La API actual no tiene /auth/me/. Primero valida el token con una ruta
  // protegida y luego lee sus datos de presentación; los permisos los decide Django.
  me: async () => {
    await request("/categorias/");
    try {
      const payload = getToken().split(".")[1].replace(/-/g, "+").replace(/_/g, "/");
      const bytes = Uint8Array.from(atob(payload), (c) => c.charCodeAt(0));
      const datos = JSON.parse(new TextDecoder().decode(bytes));
      if (!datos.rol || !datos.username) throw new Error("Token sin identidad");
      return { rol: datos.rol, username: datos.username };
    } catch {
      cerrarSesion();
      const error = new Error("No se pudo validar la sesión. Ingresa nuevamente.");
      error.status = 401;
      throw error;
    }
  },
};

// Los precios viajan como string decimal ("12.50") para no perder exactitud (RNF7).
const IMAGENES_INCLUIDAS = new Set([
  "cafe", "cocoa", "cocoa-con-leche", "empanada", "leche", "pan",
  "sandwich-de-huevo", "te", "trozo-de-rollo", "trozo-de-torta",
]);

function imagenIncluida(producto) {
  const clave = producto.nombre.normalize("NFD").replace(/[\u0300-\u036f]/g, "")
    .toLowerCase().trim().replace(/\s+/g, "-");
  return producto.imagen || (IMAGENES_INCLUIDAS.has(clave) ? `/images/productos/${clave}.jpg` : "");
}

export const productosApi = {
  listar: async ({ q = "", categoria = "" } = {}) => {
    const productos = [];
    let pagina = 1;
    let siguiente = true;
    while (siguiente) {
      const params = new URLSearchParams({ q, categoria, page: String(pagina), page_size: "100" });
      const respuesta = await request(`/productos/?${params}`);
      const items = Array.isArray(respuesta) ? respuesta : respuesta?.results;
      if (!Array.isArray(items)) throw new Error("La respuesta del catálogo no es válida.");
      productos.push(...items.map((producto) => ({ ...producto, imagen: imagenIncluida(producto) })));
      siguiente = !Array.isArray(respuesta) && Boolean(respuesta.next);
      pagina += 1;
    }
    return productos;
  },
  categorias: () => request("/categorias/"),
  crear: (datos) => request("/productos/", { method: "POST", body: JSON.stringify(datos) }),
  actualizar: (id, datos) =>
    request(`/productos/${id}/`, { method: "PATCH", body: JSON.stringify(datos) }),
};

async function pedidosConPagos() {
  const [pedidos, pagos] = await Promise.all([request("/pedidos/"), request("/pagos/")]);
  return pedidos.map((pedido) => ({ ...pedido, pago: pagos.find((pago) => pago.pedido === pedido.id) || null }));
}

export const pedidosApi = {
  crear: (datos) => request("/pedidos/", { method: "POST", body: JSON.stringify(datos) }),
  listarCocina: () => request("/pedidos/?estado=ESPERA,EN_PREPARACION,LISTO"),
  listarMesero: () => request("/pedidos/?estado=ESPERA,EN_PREPARACION,LISTO"),
  listarCaja: pedidosConPagos,
  listarAdministrador: pedidosConPagos,
  cambiarEstado: (id, estado) =>
    request(`/pedidos/${id}/estado/`, { method: "PATCH", body: JSON.stringify({ estado }) }),
  cancelar: (id) => request(`/pedidos/${id}/cancelar/`, { method: "POST", body: "{}" }),
  registrarPago: (id, datos) => request("/pagos/", {
    method: "POST", body: JSON.stringify({ pedido: id, monto: datos.monto, metodo: datos.metodo, referencia_qr: datos.referencia_qr || "" }),
  }),
  verificarQr: (id) => request(`/pagos/${id}/confirmar/`, { method: "POST", body: "{}" }),
  registrarReembolso: (id, datos) => request(`/pagos/${id}/reembolsar/`, { method: "POST", body: JSON.stringify({ motivo: datos.motivo }) }),
};

export const reportesApi = {
  conciliacion: (datos) => request("/pagos/conciliacion/", { method: "POST", body: JSON.stringify(datos) }),
  ventas: (desde, hasta) => request(`/pagos/reporte-ventas/?${new URLSearchParams({ desde, hasta })}`),
};

export const usuariosApi = {
  listar: () => request("/usuarios/"),
  crear: (datos) => request("/usuarios/", { method: "POST", body: JSON.stringify(datos) }),
};
