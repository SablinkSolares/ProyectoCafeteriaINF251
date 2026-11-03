import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { productosApi } from "../api";
import Catalogo from "./Catalogo";

vi.mock("../api", () => ({
  getRol: () => "administrador",
  productosApi: {
    categorias: vi.fn(),
    listar: vi.fn(),
    crear: vi.fn(),
    actualizar: vi.fn(),
  },
}));

const PRODUCTOS = [
  { id: 2, nombre: "Café", categoria: 1, categoria_nombre: "Bebidas", precio: "7.00", stock: 15 },
  { id: 8, nombre: "Trozo de torta", categoria: 2, categoria_nombre: "Acompañamientos", precio: "12.00", stock: 3 },
  { id: 4, nombre: "Cocoa con leche", categoria: 1, categoria_nombre: "Bebidas", precio: "9.50", stock: 0 },
];

describe("Catalogo (S1-T04 / RF1 + S2-T02)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    productosApi.categorias.mockResolvedValue([
      { id: 1, nombre: "Bebidas" },
      { id: 2, nombre: "Acompañamientos" },
    ]);
    productosApi.listar.mockResolvedValue(PRODUCTOS);
  });

  it("lista productos con categoría, precio y estado de stock", async () => {
    render(<Catalogo />);

    expect(await screen.findByText("Café")).toBeInTheDocument();
    expect(screen.getByText("Bs 7.00")).toBeInTheDocument();
    expect(screen.getByText("Quedan 3")).toBeInTheDocument();
    expect(screen.getByText("Agotado")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Agregar producto" })).toBeInTheDocument();
  });

  it("filtra por categoría al tocar un chip", async () => {
    render(<Catalogo />);
    await screen.findByText("Café");

    fireEvent.click(screen.getByRole("button", { name: "Bebidas" }));

    await waitFor(() =>
      expect(productosApi.listar).toHaveBeenLastCalledWith({ q: "", categoria: "1" }),
    );
  });

  it("muestra el aviso del servidor si falla la carga", async () => {
    productosApi.listar.mockRejectedValue(new Error("Sesión expirada"));
    render(<Catalogo />);

    expect(await screen.findByRole("alert")).toHaveTextContent(/no se pudo cargar el catálogo/i);
  });
});
