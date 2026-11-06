import { useState } from "react";
import { authApi } from "../api";

export default function Login({ onIngresar, errorInicial = "", onCancelar }) {
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
      <form className="panel form login" onSubmit={enviar} noValidate>
        <div className="login-marca">
          <span className="marca-icono">D</span>
          <span>DinoCafé</span>
        </div>
        <div>
          <h1>Bienvenido</h1>
          <p className="detalle">Ingresa para continuar al sistema de cafetería.</p>
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
        {onCancelar && <button type="button" className="btn-texto" onClick={onCancelar}>Volver al catálogo</button>}
      </form>
    </main>
  );
}
