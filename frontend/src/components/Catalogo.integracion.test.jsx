import { render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import Catalogo from "./Catalogo";

afterEach(() => {
  vi.unstubAllGlobals();
  localStorage.clear();
});

it("muestra productos cuando la API responde con paginación", async () => {
  localStorage.setItem("rol", "administrador");
  const producto = { id: 1, nombre: "Café", categoria: 1, categoria_nombre: "Bebidas", precio: "7.00", stock: 15 };
  vi.stubGlobal("fetch", vi.fn(async (url) => ({
    ok: true,
    status: 200,
    json: async () => url.includes("/categorias/")
      ? [{ id: 1, nombre: "Bebidas" }]
      : { count: 1, next: null, previous: null, results: [producto] },
  })));
  render(<Catalogo />);
  expect(await screen.findByText("Café")).toBeInTheDocument();
  expect(screen.getByText("Bs 7.00")).toBeInTheDocument();
});
