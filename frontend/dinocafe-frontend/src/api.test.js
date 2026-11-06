import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { authApi, guardarSesion, pedidosApi, productosApi, reportesApi } from "./api";

function respuesta(status, datos) {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => datos,
  };
}
function token(rol = "mesero", username = "ana") {
  return `cabecera.${btoa(JSON.stringify({ rol, username }))}.firma`;
}

describe("API: renovación de sesión", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("renueva el token de acceso y reintenta la petición protegida", async () => {
    guardarSesion({
      access: "access-vencido",
      refresh: "refresh-valido",
      rol: "mesero",
      username: "ana",
    });
    const fetch = vi.fn()
      .mockResolvedValueOnce(respuesta(401, { detail: "Token expirado" }))
      .mockResolvedValueOnce(respuesta(200, { access: token() }))
      .mockResolvedValueOnce(respuesta(200, []));
    vi.stubGlobal("fetch", fetch);

    await expect(authApi.me()).resolves.toEqual({ username: "ana", rol: "mesero" });
    expect(fetch).toHaveBeenCalledTimes(3);
    expect(fetch.mock.calls[0][1].headers.Authorization).toBe("Bearer access-vencido");
    expect(fetch.mock.calls[1][0]).toContain("/auth/refresh/");
    expect(fetch.mock.calls[2][1].headers.Authorization).toBe(`Bearer ${token()}`);
    expect(localStorage.getItem("access_token")).toBe(token());
    expect(localStorage.getItem("refresh_token")).toBe("refresh-valido");
  });

  it("borra la sesión cuando el refresh token ya no es válido", async () => {
    guardarSesion({
      access: "access-vencido",
      refresh: "refresh-vencido",
      rol: "mesero",
      username: "ana",
    });
    const fetch = vi.fn()
      .mockResolvedValueOnce(respuesta(401, { detail: "Token expirado" }))
      .mockResolvedValueOnce(respuesta(401, { detail: "Refresh inválido" }));
    vi.stubGlobal("fetch", fetch);

    await expect(authApi.me()).rejects.toMatchObject({ status: 401 });
    expect(localStorage.getItem("access_token")).toBeNull();
    expect(localStorage.getItem("refresh_token")).toBeNull();
  });
});

describe("adaptación a la API actual", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("lee todas las páginas y asigna imágenes incluidas sin guardar datos falsos", async () => {
    const fetch = vi.fn()
      .mockResolvedValueOnce(respuesta(200, { next: "otra", results: [{ id: 1, nombre: "Café" }] }))
      .mockResolvedValueOnce(respuesta(200, { next: null, results: [{ id: 2, nombre: "Pan" }] }));
    vi.stubGlobal("fetch", fetch);
    const datos = await productosApi.listar({ q: "a", categoria: "1" });
    expect(datos.map((p) => p.imagen)).toEqual(["/images/productos/cafe.jpg", "/images/productos/pan.jpg"]);
    expect(fetch.mock.calls[1][0]).toContain("page=2");
    expect(fetch.mock.calls[1][0]).toContain("categoria=1");
  });

  it("utiliza los endpoints de pagos de la rama actual", async () => {
    const fetch = vi.fn().mockResolvedValue(respuesta(200, {}));
    vi.stubGlobal("fetch", fetch);
    await pedidosApi.registrarPago(8, { monto: "7.00", metodo: "QR", referencia_qr: "abc" });
    expect(fetch.mock.calls[0][0]).toContain("/pagos/");
    expect(JSON.parse(fetch.mock.calls[0][1].body)).toEqual({ pedido: 8, monto: "7.00", metodo: "QR", referencia_qr: "abc" });
    await pedidosApi.verificarQr(3);
    expect(fetch.mock.calls[1][0]).toContain("/pagos/3/confirmar/");
    await pedidosApi.registrarReembolso(3, { motivo: "Duplicado" });
    expect(fetch.mock.calls[2][0]).toContain("/pagos/3/reembolsar/");
  });

  it("consulta la conciliación diaria sin inventar un reporte por periodo", async () => {
    const fetch = vi.fn().mockResolvedValue(respuesta(200, { total_neto: "7.00" }));
    vi.stubGlobal("fetch", fetch);
    await reportesApi.conciliacion({ fecha: "2026-11-06", efectivo_real: "7.00", qr_real: "0.00" });
    expect(fetch.mock.calls[0][0]).toContain("/pagos/conciliacion/");
  });
});
