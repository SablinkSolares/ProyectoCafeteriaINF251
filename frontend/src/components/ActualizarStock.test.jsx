import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";
import { productosApi } from "../api";
import ActualizarStock from "./ActualizarStock";

vi.mock("../api", () => ({ productosApi: { actualizarStock: vi.fn() } }));
const producto = { id: 4, nombre: "Pan", stock: 12, stock_fisico: 12 };
beforeEach(() => vi.clearAllMocks());

it("guarda el nuevo stock y el valor previo para detectar cambios simultáneos", async () => {
  productosApi.actualizarStock.mockResolvedValue({});
  const actualizado = vi.fn();
  render(<ActualizarStock producto={producto} onActualizado={actualizado} onCancelar={vi.fn()} />);
  fireEvent.change(screen.getByLabelText("Nuevo stock disponible"), { target: { value: "20" } });
  fireEvent.click(screen.getByRole("button", { name: "Guardar stock" }));
  await waitFor(() => expect(productosApi.actualizarStock).toHaveBeenCalledWith(4, 20, 12));
  expect(actualizado).toHaveBeenCalledWith("Pan");
});

it("conserva el formulario y muestra el error si cambió el stock en el servidor", async () => {
  productosApi.actualizarStock.mockRejectedValue(new Error("El stock cambió mientras lo editabas."));
  const actualizado = vi.fn();
  render(<ActualizarStock producto={producto} onActualizado={actualizado} onCancelar={vi.fn()} />);
  fireEvent.click(screen.getByRole("button", { name: "Guardar stock" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("El stock cambió");
  expect(actualizado).not.toHaveBeenCalled();
});
