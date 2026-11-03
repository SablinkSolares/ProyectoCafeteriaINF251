import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import ProductoForm from "./ProductoForm";

const CATEGORIAS = [{ id: 1, nombre: "Bebidas" }];

function renderForm(props = {}) {
  return render(
    <ProductoForm
      categorias={CATEGORIAS}
      producto={null}
      puedeCambiarPrecio
      onGuardar={vi.fn().mockResolvedValue()}
      onCancelar={vi.fn()}
      {...props}
    />,
  );
}

describe("ProductoForm (S1-T04 / RF1)", () => {
  it("rechaza un precio con coma decimal", async () => {
    const onGuardar = vi.fn();
    renderForm({ onGuardar });
    const user = userEvent.setup();

    await user.type(screen.getByLabelText("Nombre"), "Café");
    await user.type(screen.getByLabelText("Precio (Bs)"), "7,50");
    await user.click(screen.getByRole("button", { name: "Guardar producto" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(/precio/i);
    expect(onGuardar).not.toHaveBeenCalled();
  });

  it("envía el precio como string decimal y el stock numérico", async () => {
    const onGuardar = vi.fn().mockResolvedValue();
    renderForm({ onGuardar });
    const user = userEvent.setup();

    await user.type(screen.getByLabelText("Nombre"), "Café");
    await user.type(screen.getByLabelText("Precio (Bs)"), "7.50");
    await user.clear(screen.getByLabelText("Stock"));
    await user.type(screen.getByLabelText("Stock"), "12");
    await user.click(screen.getByRole("button", { name: "Guardar producto" }));

    expect(onGuardar).toHaveBeenCalledWith({
      nombre: "Café",
      categoria: 1,
      precio: "7.50",
      stock: 12,
    });
  });

  it("bloquea el precio al editar sin ser administrador (RD1)", () => {
    renderForm({
      producto: { id: 2, nombre: "Café", categoria: 1, precio: "7.00", stock: 5 },
      puedeCambiarPrecio: false,
    });
    expect(screen.getByLabelText("Precio (Bs)")).toBeDisabled();
  });

  it("muestra un aviso si no hay categorías", () => {
    renderForm({ categorias: [] });
    expect(screen.getByRole("alert")).toHaveTextContent(/no hay categorías/i);
    expect(screen.getByRole("button", { name: "Guardar producto" })).toBeDisabled();
  });
});
