import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { getRol, reportesApi } from "../api";
import ReportesVentas from "./ReportesVentas";

vi.mock("../api", () => ({ getRol: vi.fn(), reportesApi: { ventas: vi.fn(), conciliacion: vi.fn() } }));

describe("Ventas y conciliación", () => {
  beforeEach(() => { vi.clearAllMocks(); getRol.mockReturnValue("administrador"); });

  it("consulta el período y muestra los importes y desgloses", async () => {
    reportesApi.ventas.mockResolvedValue({
      desde: "2026-01-01", hasta: "2026-01-31", cantidad_pagos: 1,
      total_ventas: "14.00", total_reembolsos: "0.00", total_neto: "14.00",
      categorias: [{ producto__categoria_id: 1, producto__categoria__nombre: "Bebidas", unidades: 2, total: "14.00" }],
      productos: [{ producto_id: 1, producto__nombre: "Café", producto__categoria__nombre: "Bebidas", unidades: 2, total: "14.00" }],
    });
    render(<ReportesVentas />);
    fireEvent.change(screen.getByLabelText("Desde"), { target: { value: "2026-01-01" } });
    fireEvent.change(screen.getByLabelText("Hasta"), { target: { value: "2026-01-31" } });
    fireEvent.click(screen.getByRole("button", { name: "Consultar período" }));
    await screen.findByText("Café");
    expect(reportesApi.ventas).toHaveBeenCalledWith("2026-01-01", "2026-01-31");
    expect(screen.getByText(/1 pagos confirmados/)).toBeInTheDocument();
  });

  it("no expone la consulta por período al cajero y conserva la conciliación", () => {
    getRol.mockReturnValue("cajero");
    render(<ReportesVentas />);
    expect(screen.queryByRole("button", { name: "Consultar período" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Conciliar día" })).toBeInTheDocument();
  });

  it("valida las fechas antes de consultar", async () => {
    render(<ReportesVentas />);
    fireEvent.change(screen.getByLabelText("Desde"), { target: { value: "2026-02-01" } });
    fireEvent.change(screen.getByLabelText("Hasta"), { target: { value: "2026-01-01" } });
    fireEvent.click(screen.getByRole("button", { name: "Consultar período" }));
    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent("fecha inicial"));
    expect(reportesApi.ventas).not.toHaveBeenCalled();
  });
});
