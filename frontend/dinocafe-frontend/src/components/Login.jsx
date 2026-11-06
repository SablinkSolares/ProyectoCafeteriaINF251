import { useState } from "react";
import { authApi } from "../api";

export default function Login({ onIngresar, errorInicial = "" }) {
  const [usuario, setUsuario] = useState("");
  const [clave, setClave] = useState("");
  const [error, setError] = useState(errorInicial);
  const [cargando, setCargando] = useState(false);

  async function enviar(e) {
    e.preventDefault();
    setError("");
    setCargando(true);
    try {
      const datos = await authApi.login(usuario.trim(), clave);
      await onIngresar(datos);
    } catch (err) {
      setError(err.message === "Failed to fetch"
        ? "No se pudo conectar con el servidor. Verifica que Docker esté iniciado."
        : err.status === 401 || /No active account/i.test(err.message)
          ? "Usuario o contraseña incorrectos."
          : err.message);
    } finally {
      setCargando(false);
    }
  }

  return (
    <main className="login-pagina">
      <div className="login-imagen" aria-hidden="true" />
      <section className="login-contenido" aria-label="Acceso del personal">
      <form className="form login" onSubmit={enviar}>
        <div className="login-marca">
          <span className="marca-icono" aria-hidden="true">D</span>
          <span>DinoCafé</span>
        </div>
        <div className="login-encabezado">
          <p className="login-sobretitulo">ACCESO DEL PERSONAL</p>
          <h1>Bienvenido a DinoCafé</h1>
          <p className="detalle">Ingresa con tu cuenta para continuar.</p>
        </div>
        <label>Usuario
          <input value={usuario} onChange={(e) => { setUsuario(e.target.value); setError(""); }}
            autoComplete="username" autoFocus required />
        </label>
        <label>Contraseña
          <input type="password" value={clave} onChange={(e) => { setClave(e.target.value); setError(""); }}
            autoComplete="current-password" required />
        </label>
        {error && <p className="error" role="alert">{error}</p>}
        <button type="submit" className="btn" disabled={cargando}>
          {cargando ? "Ingresando…" : "Ingresar"}
        </button>
      </form>
      </section>
    </main>
  );
}
