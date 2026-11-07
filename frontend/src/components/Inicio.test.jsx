import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";
import { menuApi } from "../api";
import Inicio from "./Inicio";

vi.mock("../api", () => ({ menuApi: { obtener: vi.fn() } }));
const MENU = {
  categorias: [{ id: 1, nombre: "Bebidas" }, { id: 2, nombre: "Acompañamientos" }],
  productos: [{ id: 1, nombre: "Café", categoria: 1, categoria_nombre: "Bebidas", precio: "7.00", imagen: "/images/productos/cafe.jpg" }, { id: 2, nombre: "Pan", categoria: 2, categoria_nombre: "Acompañamientos", precio: "3.00", imagen: "/images/productos/pan.jpg" }],
};
beforeEach(() => { vi.clearAllMocks(); menuApi.obtener.mockResolvedValue(MENU); });

it("muestra descripción, productos y precios sin controles administrativos", async () => {
  render(<Inicio onAcceder={vi.fn()} />);
  expect(await screen.findByRole("heading", { name: "Café" })).toBeInTheDocument();
  expect(screen.getByText(/Un espacio para hacer una pausa/)).toBeInTheDocument();
  expect(screen.getByAltText("Café")).toHaveAttribute("src", "/images/productos/cafe.jpg");
  expect(screen.queryByRole("button", { name: /stock|Agregar producto|Editar|Desactivar/i })).not.toBeInTheDocument();
});

it("filtra el menú por categoría", async () => {
  render(<Inicio onAcceder={vi.fn()} />);
  await screen.findByRole("heading", { name: "Pan" });
  fireEvent.click(screen.getByRole("button", { name: "Bebidas", exact: true }));
  expect(screen.getByRole("heading", { name: "Café" })).toBeInTheDocument();
  expect(screen.queryByRole("heading", { name: "Pan" })).not.toBeInTheDocument();
});

it("permite acceder al inicio de sesión del personal", () => {
  const acceder = vi.fn();
  render(<Inicio onAcceder={acceder} />);
  fireEvent.click(screen.getByRole("button", { name: "Acceso del personal" }));
  expect(acceder).toHaveBeenCalledOnce();
});

it("permite reintentar cuando el menú no se puede cargar", async () => {
  menuApi.obtener.mockRejectedValueOnce(new Error("Sin conexión"));
  render(<Inicio onAcceder={vi.fn()} />);
  expect(await screen.findByRole("alert")).toHaveTextContent("Sin conexión");
  fireEvent.click(screen.getByRole("button", { name: "Volver a intentar" }));
  expect(await screen.findByRole("heading", { name: "Café" })).toBeInTheDocument();
});
