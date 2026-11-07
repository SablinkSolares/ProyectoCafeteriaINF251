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
vi.mock("./components/Login", () => ({ default: ({ onVolver }) => <div>Formulario de acceso<button onClick={onVolver}>Volver al menú</button></div> }));
vi.mock("./components/Inicio", () => ({ default: ({ onAcceder, sesionActiva }) => <div>Menú público<button onClick={onAcceder}>{sesionActiva ? "Volver al panel" : "Acceso del personal"}</button></div> }));
vi.mock("./components/ReportesVentas", () => ({ default: () => <div>Ventas protegidas</div> }));
vi.mock("./components/VistaCaja", () => ({ default: () => <div>Caja protegida</div> }));
vi.mock("./components/VistaCocina", () => ({ default: () => <div>Cocina protegida</div> }));
vi.mock("./components/VistaMesero", () => ({ default: () => <div>Pedidos protegidos</div> }));
vi.mock("./components/Notificaciones", () => ({ default: () => null }));

describe("App: sesión y acceso por rol", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    window.history.replaceState(null, "", "/");
  });

  it("valida la sesión con el servidor y no confía en un rol guardado localmente", async () => {
    localStorage.setItem("access_token", "token");
    localStorage.setItem("rol", "administrador");
    authApi.me.mockResolvedValue({ username: "mesero", rol: "mesero" });
    window.history.replaceState(null, "", "/#pedidos");
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
    expect(screen.getByText("Menú público")).toBeInTheDocument();
    expect(screen.queryByText("Catálogo protegido")).not.toBeInTheDocument();
  });

  it("muestra el menú público por defecto y separa el acceso del personal", () => {
    render(<App />);
    expect(screen.getByText("Menú público")).toBeInTheDocument();
    expect(screen.queryByText("Catálogo protegido")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Acceso del personal" }));
    expect(screen.getByText("Formulario de acceso")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Volver al menú" }));
    expect(screen.getByText("Menú público")).toBeInTheDocument();
  });

  it("no abre el sistema si el servidor rechaza la sesión guardada", async () => {
    localStorage.setItem("access_token", "vencido");
    authApi.me.mockRejectedValue(Object.assign(new Error("Unauthorized"), { status: 401 }));
    window.history.replaceState(null, "", "/#login");
    render(<App />);

    expect(await screen.findByText("Formulario de acceso")).toBeInTheDocument();
    expect(cerrarSesion).toHaveBeenCalled();
  });

  it("permite consultar la portada con sesión activa y volver al panel", async () => {
    localStorage.setItem("access_token", "token");
    authApi.me.mockResolvedValue({ username: "admin", rol: "administrador" });
    render(<App />);
    expect(await screen.findByText("Menú público")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Volver al panel" }));
    expect(screen.getByText("Catálogo protegido")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Ver menú" }));
    expect(screen.getByText("Menú público")).toBeInTheDocument();
  });
});
