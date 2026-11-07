import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { usuariosApi } from "../api";
import GestionUsuarios from "./GestionUsuarios";

vi.mock("../api", () => ({ usuariosApi: { listar: vi.fn(), crear: vi.fn() } }));

describe("Creación de cuentas", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    usuariosApi.listar.mockResolvedValue([{ id: 1, username: "admin", first_name: "", last_name: "", rol: "administrador", is_active: true }]);
    usuariosApi.crear.mockResolvedValue({ id: 2 });
  });

  it("consulta las cuentas y envía una nueva cuenta con rol y contraseña", async () => {
    render(<GestionUsuarios />);
    expect(await screen.findByText("admin")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Nuevo usuario" }));
    fireEvent.change(screen.getByLabelText("Nombre de usuario"), { target: { value: "ana" } });
    fireEvent.change(screen.getByLabelText("Rol"), { target: { value: "cajero" } });
    fireEvent.change(screen.getByLabelText("Contraseña inicial"), { target: { value: "ClavePrueba2" } });
    fireEvent.click(screen.getByRole("button", { name: "Crear cuenta" }));
    await waitFor(() => expect(usuariosApi.crear).toHaveBeenCalledWith(expect.objectContaining({ username: "ana", rol: "cajero", password: "ClavePrueba2" })));
    expect(await screen.findByRole("status")).toHaveTextContent("Cuenta creada");
    expect(screen.queryByLabelText("Contraseña inicial")).not.toBeInTheDocument();
    expect(usuariosApi.listar).toHaveBeenCalledTimes(2);
  });

  it("muestra un error del servidor y conserva el formulario para corregirlo", async () => {
    usuariosApi.crear.mockRejectedValue(new Error("Ya existe un usuario con ese nombre."));
    render(<GestionUsuarios />);
    fireEvent.click(screen.getByRole("button", { name: "Nuevo usuario" }));
    fireEvent.change(screen.getByLabelText("Nombre de usuario"), { target: { value: "admin" } });
    fireEvent.change(screen.getByLabelText("Contraseña inicial"), { target: { value: "ClavePrueba2" } });
    fireEvent.click(screen.getByRole("button", { name: "Crear cuenta" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Ya existe");
    expect(screen.getByLabelText("Nombre de usuario")).toHaveValue("admin");
  });
});
