import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { pedidosApi, productosApi } from "../api";
import VistaMesero from "./VistaMesero";

vi.mock("../api", () => ({
  pedidosApi: {
    listarMesero: vi.fn(),
    cambiarEstado: vi.fn(),
  },
  productosApi: { listar: vi.fn(), categorias: vi.fn() },
}));

const PEDIDO = {
  id: 12,
  mesa: 3,
  estado: "LISTO",
  total: "15.00",
  detalles: [{ id: 1, producto: "Café", cantidad: 2, stock: 5 }],
};

describe("VistaMesero", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    pedidosApi.listarMesero.mockResolvedValue([PEDIDO]);
    pedidosApi.cambiarEstado.mockResolvedValue({ ...PEDIDO, estado: "ENTREGADO" });
    productosApi.listar.mockResolvedValue([]);
    productosApi.categorias.mockResolvedValue([]);
  });

  it("consulta los pedidos listos y registra su entrega", async () => {
    render(<VistaMesero />);
    expect(await screen.findByText("#12")).toBeInTheDocument();
    expect(screen.getByText("Listo para entregar")).toBeInTheDocument();
    expect(screen.queryByText(/Mesa 3/)).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Confirmar entrega" }));
    await waitFor(() => expect(pedidosApi.cambiarEstado).toHaveBeenCalledWith(12, "ENTREGADO"));
    await waitFor(() => expect(screen.queryByText("#12")).not.toBeInTheDocument());
  });
});
