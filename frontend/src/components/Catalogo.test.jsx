import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { getRol, productosApi } from "../api";
import Catalogo from "./Catalogo";

vi.mock("../api", () => ({
  getRol: vi.fn(() => "administrador"),
  productosApi: {
    categorias: vi.fn(),
    listar: vi.fn(),
    crear: vi.fn(),
    actualizar: vi.fn(),
    actualizarStock: vi.fn(),
  },
}));

const PRODUCTOS = [
  { id: 2, nombre: "Café", categoria: 1, categoria_nombre: "Bebidas", precio: "7.00", stock: 15, imagen: "/images/productos/cafe.jpg", activo: true },
  { id: 8, nombre: "Trozo de torta", categoria: 2, categoria_nombre: "Acompañamientos", precio: "12.00", stock: 3, imagen: "", activo: true },
  { id: 4, nombre: "Cocoa con leche", categoria: 1, categoria_nombre: "Bebidas", precio: "9.50", stock: 0, imagen: "", activo: true },
];

describe("Catalogo (S1-T04 / RF1 + S2-T02)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    getRol.mockReturnValue("administrador");
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
      expect(productosApi.listar).toHaveBeenLastCalledWith({ q: "", categoria: "1", activo: "" }),
    );
  });

  it("desactiva conservando el producto en el historial", async () => {
    vi.spyOn(window, "confirm").mockReturnValue(true);
    productosApi.actualizar.mockResolvedValue({ ...PRODUCTOS[0], activo: false });
    render(<Catalogo />);
    expect(await screen.findByText("Café")).toBeInTheDocument();
    fireEvent.click(screen.getAllByRole("button", { name: "Desactivar" })[0]);
    await waitFor(() => expect(productosApi.actualizar).toHaveBeenCalledWith(2, { activo: false }));
    vi.restoreAllMocks();
  });

  it("muestra el aviso del servidor si falla la carga", async () => {
    productosApi.listar.mockRejectedValue(new Error("Sesión expirada"));
    render(<Catalogo />);

    expect(await screen.findByRole("alert")).toHaveTextContent(/no se pudo cargar el catálogo/i);
  });

  it("permite al administrador actualizar stock desde el catálogo", async () => {
    productosApi.actualizarStock.mockResolvedValue({});
    render(<Catalogo />);
    fireEvent.click(await screen.findByRole("button", { name: "Actualizar stock de Trozo de torta" }));
    fireEvent.change(screen.getByLabelText("Nuevo stock disponible"), { target: { value: "9" } });
    productosApi.listar.mockResolvedValue(PRODUCTOS.map(p => p.id === 8 ? { ...p, stock: 9 } : p));
    fireEvent.click(screen.getByRole("button", { name: "Guardar stock" }));
    await waitFor(() => expect(productosApi.actualizarStock).toHaveBeenCalledWith(8, 9, 3));
    expect(await screen.findByRole("status")).toHaveTextContent("Stock de Trozo de torta actualizado.");
    expect(await screen.findByText("Disponible: 9")).toBeInTheDocument();
  });

  it("no ofrece edición de stock a otros roles", async () => {
    getRol.mockReturnValue("mesero");
    render(<Catalogo />);
    await screen.findByText("Café");
    expect(screen.queryByRole("button", { name: /Actualizar stock/ })).not.toBeInTheDocument();
  });

  it("dirige los productos preparables a la gestión de insumos", async () => {
    productosApi.listar.mockResolvedValue([{ ...PRODUCTOS[0], preparable: true }]);
    render(<Catalogo />);
    expect(await screen.findByRole("link", { name: "Actualizar insumos de Café" })).toHaveAttribute("href", "#inventario");
    expect(screen.queryByRole("button", { name: "Actualizar stock de Café" })).not.toBeInTheDocument();
  });

  it("no consulta el catálogo protegido sin iniciar sesión", async () => {
    render(<Catalogo publico onLogin={() => {}} />);
    expect(await screen.findByText(/catálogo requiere acceso del personal/i)).toBeInTheDocument();
    expect(productosApi.listar).not.toHaveBeenCalled();
    expect(productosApi.categorias).not.toHaveBeenCalled();
  });
});
