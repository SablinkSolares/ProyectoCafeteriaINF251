import { useState } from "react";
import { authApi, guardarSesion } from "../api";

// Acceso provisional de pruebas. La pantalla definitiva de login y rutas
// protegidas corresponde a S1-T02 (Noemi); esta versión solo permite probar
// las vistas de Carlos con usuarios reales del backend.
const CUENTAS = [
  { rol: "administrador", usuario: "admin", clave: "admin123" },
  { rol: "mesero", usuario: "mesero", clave: "mesero123" },
  { rol: "cajero", usuario: "cajero", clave: "cajero123" },
  { rol: "cocina", usuario: "cocina", clave: "cocina123" },
];

export default function LoginDev({ onIngresar }) {
  const [usuario, setUsuario] = useState("admin");
  const [clave, setClave] = useState("admin123");
  const [error, setError] = useState("");
  const [cargando, setCargando] = useState(false);

  async function enviar(e) {
    e.preventDefault();
    setError("");
    setCargando(true);
    try {
      const datos = await authApi.login(usuario.trim(), clave);
      guardarSesion(datos);
      onIngresar(datos.rol);
    } catch (err) {
      const mensaje =
        err.message === "Failed to fetch"
          ? "No se pudo conectar con el backend (http://localhost:8000). Verifica que esté corriendo."
          : /No active account/i.test(err.message)
            ? "Usuario o contraseña incorrectos."
            : err.message;
      setError(mensaje);
    } finally {
      setCargando(false);
    }
  }

  function usarCuenta(cuenta) {
    setUsuario(cuenta.usuario);
    setClave(cuenta.clave);
    setError("");
  }

  return (
    <main className="contenedor">
      <form className="panel form login" onSubmit={enviar}>
        <div>
          <h1>DinoCafé</h1>
          <p className="detalle">
            Acceso provisional de pruebas. La pantalla definitiva corresponde a S1-T02.
          </p>
        </div>
        <label>Usuario
          <input
            value={usuario}
            onChange={(e) => setUsuario(e.target.value)}
            autoComplete="username"
            autoFocus
          />
        </label>
        <label>Contraseña
          <input
            type="password"
            value={clave}
            onChange={(e) => setClave(e.target.value)}
            autoComplete="current-password"
          />
        </label>
        {error && <p className="error" role="alert">{error}</p>}
        <button type="submit" className="btn" disabled={cargando}>
          {cargando ? "Ingresando…" : "Ingresar"}
        </button>
        <div className="cuentas">
          <p className="detalle">Cuentas de prueba (tocar para completar):</p>
          <div className="chips">
            {CUENTAS.map((c) => (
              <button type="button" key={c.rol} className="chip" onClick={() => usarCuenta(c)}>
                {c.rol}
              </button>
            ))}
          </div>
          <p className="detalle">admin/admin123 · mesero/mesero123 · cajero/cajero123 · cocina/cocina123</p>
        </div>
      </form>
    </main>
  );
}
