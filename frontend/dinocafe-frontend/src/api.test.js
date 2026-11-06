import { afterEach, describe, expect, it, vi } from "vitest";
import { productosApi } from "./api";

afterEach(() => vi.unstubAllGlobals());

describe("catálogo paginado", () => {
  it("devuelve los productos de todas las páginas manteniendo los filtros", async () => {
    const fetch = vi.fn()
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({ count: 2, next: "siguiente", results: [{ id: 1, nombre: "Café" }] }) })
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({ count: 2, next: null, results: [{ id: 2, nombre: "Té" }] }) });
    vi.stubGlobal("fetch", fetch);

    expect(await productosApi.listar({ q: "bebida", categoria: "1" })).toEqual([
      { id: 1, nombre: "Café" }, { id: 2, nombre: "Té" },
    ]);
    expect(fetch).toHaveBeenCalledTimes(2);
    expect(fetch.mock.calls[1][0]).toContain("q=bebida");
    expect(fetch.mock.calls[1][0]).toContain("categoria=1");
    expect(fetch.mock.calls[1][0]).toContain("page=2");
  });

  it("acepta la respuesta de lista sin paginación", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => [{ id: 1 }] }));
    expect(await productosApi.listar()).toEqual([{ id: 1 }]);
  });
});
