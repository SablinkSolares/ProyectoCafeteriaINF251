import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { pedidosApi } from "../api";
import VistaCocina from "./VistaCocina";

vi.mock("../api", () => ({
  pedidosApi: {
    listarCocina: vi.fn(),
    cambiarEstado: vi.fn(),
  },
}));

const PEDIDO = {
  id: 7,
  estado: "ESPERA",
  creado_en: new Date(Date.now() - 3 * 60000).toISOString(),
  detalles: [{ id: 1, producto: "Café", cantidad: 2, stock: 3 }],
};

describe("VistaCocina (S1-T08 / RF3 + RF5)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    pedidosApi.listarCocina.mockResolvedValue([PEDIDO]);
  });

  it("muestra el pedido reservado sin confundirlo con el stock disponible y avanza a EN_PREPARACION", async () => {
    pedidosApi.cambiarEstado.mockResolvedValue({ ...PEDIDO, estado: "EN_PREPARACION" });
    render(<VistaCocina />);

    expect(await screen.findByText("#7")).toBeInTheDocument();
    expect(screen.queryByText("Quedan 3")).not.toBeInTheDocument();
    expect(screen.getByText(/2 ítems/)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /empezar a preparar del pedido 7/i }));

    await waitFor(() =>
      expect(pedidosApi.cambiarEstado).toHaveBeenCalledWith(7, "EN_PREPARACION"),
    );
    expect(
      await screen.findByRole("button", { name: /marcar como listo del pedido 7/i }),
    ).toBeInTheDocument();
  });

  it("muestra el error del servidor si la transición es rechazada", async () => {
    pedidosApi.cambiarEstado.mockRejectedValue(new Error("Transición inválida"));
    render(<VistaCocina />);
    await screen.findByText("#7");

    fireEvent.click(screen.getByRole("button", { name: /empezar a preparar del pedido 7/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Transición inválida");
  });
});
