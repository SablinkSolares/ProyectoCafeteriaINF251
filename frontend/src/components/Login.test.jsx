import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { authApi } from "../api";
import Login from "./Login";

vi.mock("../api", () => ({
  authApi: { login: vi.fn() },
}));

describe("Login", () => {
  beforeEach(() => vi.clearAllMocks());

  it("autentica contra el backend y no muestra accesos de demostración", async () => {
    const sesion = {
      access: "access-token",
      refresh: "refresh-token",
      username: "admin",
      rol: "administrador",
    };
    const onIngresar = vi.fn();
    authApi.login.mockResolvedValue(sesion);
    render(<Login onIngresar={onIngresar} />);

    expect(screen.queryByText("Acceso de demostración")).not.toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Usuario"), { target: { value: "admin" } });
    fireEvent.change(screen.getByLabelText("Contraseña"), { target: { value: "clave" } });
    fireEvent.click(screen.getByRole("button", { name: "Ingresar" }));

    await waitFor(() => expect(authApi.login).toHaveBeenCalledWith("admin", "clave"));
    expect(onIngresar).toHaveBeenCalledWith(sesion);
  });

  it("muestra un error de credenciales sin conceder acceso", async () => {
    authApi.login.mockRejectedValue(Object.assign(new Error("Unauthorized"), { status: 401 }));
    render(<Login onIngresar={vi.fn()} />);
    fireEvent.change(screen.getByLabelText("Usuario"), { target: { value: "alguien" } });
    fireEvent.change(screen.getByLabelText("Contraseña"), { target: { value: "incorrecta" } });
    fireEvent.click(screen.getByRole("button", { name: "Ingresar" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Usuario o contraseña incorrectos.");
  });
});
