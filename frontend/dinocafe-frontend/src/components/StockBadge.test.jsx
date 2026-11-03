import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import StockBadge, { nivelStock } from "./StockBadge";

describe("StockBadge (S2-T02 / RF4)", () => {
  it("clasifica los niveles con el umbral de 5 unidades", () => {
    expect(nivelStock(0)).toBe("agotado");
    expect(nivelStock(1)).toBe("bajo");
    expect(nivelStock(5)).toBe("bajo");
    expect(nivelStock(6)).toBe("ok");
  });

  it("muestra Agotado cuando no hay existencias", () => {
    render(<StockBadge stock={0} />);
    expect(screen.getByText("Agotado")).toBeInTheDocument();
  });

  it("muestra la cantidad restante cuando el stock es bajo", () => {
    render(<StockBadge stock={3} />);
    expect(screen.getByText("Quedan 3")).toBeInTheDocument();
    expect(screen.getByTitle(/stock bajo/i)).toBeInTheDocument();
  });

  it("muestra Disponible con stock suficiente", () => {
    render(<StockBadge stock={20} />);
    expect(screen.getByText("Disponible")).toBeInTheDocument();
  });

  it("no renderiza nada si el stock no está definido", () => {
    const { container } = render(<StockBadge stock={null} />);
    expect(container).toBeEmptyDOMElement();
  });
});
