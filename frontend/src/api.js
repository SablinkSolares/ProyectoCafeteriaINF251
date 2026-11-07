// Capa de presentación: único punto de contacto con la API REST de Django (RNF5).
const BASE = import.meta.env.VITE_API_URL || "/api";

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

function mensajeError(valor) {
  if (Array.isArray(valor)) return valor.map(mensajeError).join(" ");
  if (valor && typeof valor === "object") return Object.values(valor).map(mensajeError).join(" ");
  return String(valor ?? "");
}

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
      ...(!(options.body instanceof FormData) && { "Content-Type": "application/json" }),
      ...(token && { Authorization: `Bearer ${token}` }),
      ...options.headers,
    },
  });
  const esAcceso = path === "/auth/login/" || path === "/auth/refresh/";
  const esPublica = esAcceso || path === "/menu/";
  let res = await enviar(esPublica ? null : getToken());
  if (res.status === 401 && reintentar && !esPublica) {
    res = await enviar(await renovarSesion());
  }
  if (!res.ok) {
    let detalle = "";
    try {
      const d = await res.json();
      detalle = mensajeError(d.detail || d);
    } catch { /* respuesta sin cuerpo JSON */ }
    const error = new Error(detalle || `Error ${res.status}`);
    error.status = res.status;
    throw error;
  }
  return res.status === 204 ? null : options.responseType === "blob" ? res.blob() : res.json();
}

export const authApi = {
  login: (username, password) =>
    request("/auth/login/", { method: "POST", body: JSON.stringify({ username, password }) }),
  // El servidor valida la identidad y el rol actuales de la cuenta.
  me: () => request("/auth/me/"),
};

export const menuApi = { obtener: () => request("/menu/") };

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
  listar: async ({ q = "", categoria = "", activo = "" } = {}) => {
    const productos = [];
    let pagina = 1;
    let siguiente = true;
    while (siguiente) {
      const params = new URLSearchParams({ q, categoria, activo, page: String(pagina), page_size: "100" });
      const respuesta = await request(`/productos/?${params}`);
      const items = Array.isArray(respuesta) ? respuesta : respuesta?.results;
      if (!Array.isArray(items)) throw new Error("La respuesta del catálogo no es válida.");
      productos.push(...items.map((producto) => ({ ...producto, stock_fisico: producto.stock, stock: producto.stock_disponible ?? producto.stock, imagen: imagenIncluida(producto) })));
      siguiente = !Array.isArray(respuesta) && Boolean(respuesta.next);
      pagina += 1;
    }
    return productos;
  },
  categorias: () => request("/categorias/"),
  crear: (datos) => request("/productos/", { method: "POST", body: JSON.stringify(datos) }),
  actualizar: (id, datos) =>
    request(`/productos/${id}/`, { method: "PATCH", body: JSON.stringify(datos) }),
  actualizarStock: (id, stock, stockAnterior) =>
    request(`/productos/${id}/stock/`, { method: "PATCH", body: JSON.stringify({ stock, stock_anterior: stockAnterior }) }),
};

async function pedidosConPagos(fecha = "") {
  return request(`/pedidos/?${new URLSearchParams({ fecha })}`);
}

export const pedidosApi = {
  crear: (datos) => request("/pedidos/", { method: "POST", body: JSON.stringify(datos) }),
  listarCocina: () => request("/pedidos/?estado=ESPERA,EN_PREPARACION,LISTO"),
  listarMesero: () => request("/pedidos/?estado=ESPERA,EN_PREPARACION,LISTO"),
  listarCaja: pedidosConPagos,
  listarAdministrador: pedidosConPagos,
  cambiarEstado: (id, estado) =>
    request(`/pedidos/${id}/estado/`, { method: "PATCH", body: JSON.stringify({ estado }) }),
  cancelar: (id, motivo) => request(`/pedidos/${id}/cancelar/`, { method: "POST", body: JSON.stringify({ motivo }) }),
  cambiar: (id, datos) => request(`/pedidos/${id}/cambiar/`, { method: "POST", body: JSON.stringify(datos) }),
  obtener: (id) => request(`/pedidos/${id}/`),
  registrarPago: (id, datos) => request("/pagos/", {
    method: "POST", body: JSON.stringify({ pedido: id, monto: datos.monto, monto_recibido: datos.monto_recibido || datos.monto, metodo: datos.metodo, referencia_qr: datos.referencia_qr || "" }),
  }),
  verificarQr: (id) => request(`/pagos/${id}/confirmar/`, { method: "POST", body: "{}" }),
  registrarReembolso: (id, datos) => request(`/pagos/${id}/reembolsar/`, { method: "POST", body: JSON.stringify({ motivo: datos.motivo }) }),
};

export const reportesApi = {
  conciliacion: (datos) => request("/pagos/conciliacion/", { method: "POST", body: JSON.stringify(datos) }),
  ventas: (desde, hasta) => request(`/pagos/reporte-ventas/?${new URLSearchParams({ desde, hasta })}`),
  historial: (desde, hasta) => request(`/reportes/?${new URLSearchParams({ desde, hasta })}`),
  generar: (datos) => request("/reportes/", { method: "POST", body: JSON.stringify(datos) }),
  descargar: async (id) => {
    const blob = await request(`/reportes/${id}/pdf/`, { responseType: "blob" });
    const url = URL.createObjectURL(blob);
    const enlace = document.createElement("a");
    enlace.href = url;
    enlace.download = `dinocafe-reporte-${id}.pdf`;
    enlace.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  },
};

export const inventarioApi = {
  listar: () => request("/insumos/"),
  crear: (datos) => request("/insumos/", { method: "POST", body: JSON.stringify(datos) }),
  actualizar: (id, datos) => request(`/insumos/${id}/`, { method: "PATCH", body: JSON.stringify(datos) }),
  subirImagen: (archivo) => { const body = new FormData(); body.append("imagen", archivo); return request("/imagenes/", { method: "POST", body }); },
};

export const configuracionApi = {
  obtener: () => request("/configuracion-pago/"),
  guardar: (datos) => request("/configuracion-pago/", { method: "PATCH", body: JSON.stringify(datos) }),
};

export const notificacionesApi = { listar: (despues = 0) => request(`/notificaciones/?despues=${despues}`) };

export const usuariosApi = {
  listar: () => request("/usuarios/"),
  crear: (datos) => request("/usuarios/", { method: "POST", body: JSON.stringify(datos) }),
};
