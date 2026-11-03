import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import BuscadorProductos from "./BuscadorProductos";

describe("BuscadorProductos (S2-T08 / RF9)", () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());

  it("espera 300 ms y busca el texto sin espacios", () => {
    const onBuscar = vi.fn();
    render(<BuscadorProductos onBuscar={onBuscar} retraso={300} />);
    const input = screen.getByRole("searchbox");

    fireEvent.change(input, { target: { value: "  café  " } });
    expect(onBuscar).not.toHaveBeenCalledWith("café");

    vi.advanceTimersByTime(299);
    expect(onBuscar).not.toHaveBeenCalledWith("café");

    vi.advanceTimersByTime(1);
    expect(onBuscar).toHaveBeenCalledWith("café");
  });

  it("limpia con el botón y avisa al catálogo", () => {
    const onBuscar = vi.fn();
    render(<BuscadorProductos onBuscar={onBuscar} retraso={300} />);
    const input = screen.getByRole("searchbox");

    fireEvent.change(input, { target: { value: "café" } });
    fireEvent.click(screen.getByRole("button", { name: /limpiar/i }));

    expect(input).toHaveValue("");
    expect(onBuscar).toHaveBeenCalledWith("");
  });

  it("limpia con la tecla Escape", () => {
    const onBuscar = vi.fn();
    render(<BuscadorProductos onBuscar={onBuscar} retraso={300} />);
    const input = screen.getByRole("searchbox");

    fireEvent.change(input, { target: { value: "café" } });
    fireEvent.keyDown(input, { key: "Escape" });

    expect(input).toHaveValue("");
    expect(onBuscar).toHaveBeenCalledWith("");
  });
});
