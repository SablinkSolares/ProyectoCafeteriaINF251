import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { authApi, cerrarSesion, guardarSesion } from "./api";
import App from "./App";

vi.mock("./api", () => ({
  authApi: { me: vi.fn() },
  cerrarSesion: vi.fn(),
  getToken: () => localStorage.getItem("access_token"),
  guardarSesion: vi.fn(),
}));

vi.mock("./components/Catalogo", () => ({ default: () => <div>Catálogo protegido</div> }));
vi.mock("./components/GestionUsuarios", () => ({ default: () => <div>Usuarios protegidos</div> }));
vi.mock("./components/Login", () => ({ default: () => <div>Formulario de acceso</div> }));
vi.mock("./components/ReportesVentas", () => ({ default: () => <div>Ventas protegidas</div> }));
vi.mock("./components/VistaCaja", () => ({ default: () => <div>Caja protegida</div> }));
vi.mock("./components/VistaCocina", () => ({ default: () => <div>Cocina protegida</div> }));
vi.mock("./components/VistaMesero", () => ({ default: () => <div>Pedidos protegidos</div> }));

describe("App: sesión y acceso por rol", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
  });

  it("valida la sesión con el servidor y no confía en un rol guardado localmente", async () => {
    localStorage.setItem("access_token", "token");
    localStorage.setItem("rol", "administrador");
    authApi.me.mockResolvedValue({ username: "mesero", rol: "mesero" });
    render(<App />);

    expect(await screen.findByRole("button", { name: "Entregas" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Usuarios" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Ventas" })).not.toBeInTheDocument();
    expect(guardarSesion).toHaveBeenCalledWith({
      access: "token",
      username: "mesero",
      rol: "mesero",
    });

    fireEvent.click(screen.getByRole("button", { name: "Salir" }));
    await waitFor(() => expect(cerrarSesion).toHaveBeenCalled());
    expect(screen.getByText("Catálogo protegido")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Acceso del personal" })).toBeInTheDocument();
  });

  it("muestra el catálogo público sin sesión y ofrece acceso al personal", () => {
    render(<App />);
    expect(screen.getByText("Catálogo protegido")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Acceso del personal" }));
    expect(screen.getByText("Formulario de acceso")).toBeInTheDocument();
  });

  it("no abre el sistema si el servidor rechaza la sesión guardada", async () => {
    localStorage.setItem("access_token", "vencido");
    authApi.me.mockRejectedValue(Object.assign(new Error("Unauthorized"), { status: 401 }));
    render(<App />);

    expect(await screen.findByText("Catálogo protegido")).toBeInTheDocument();
    expect(cerrarSesion).toHaveBeenCalled();
  });
});
