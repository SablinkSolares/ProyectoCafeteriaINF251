import { useCallback, useEffect, useState } from "react";
import { usuariosApi } from "../api";

const ROLES = [
  ["administrador", "Administrador"],
  ["mesero", "Mesero"],
  ["cajero", "Cajero"],
  ["cocina", "Personal de cocina"],
];
const FORM_VACIO = { username: "", first_name: "", last_name: "", email: "", rol: "mesero", password: "" };

export default function GestionUsuarios() {
  const [usuarios, setUsuarios] = useState([]);
  const [form, setForm] = useState(null);
  const [cargandoLista, setCargandoLista] = useState(true);
  const [guardando, setGuardando] = useState(false);
  const [error, setError] = useState("");
  const [aviso, setAviso] = useState("");

  const cargar = useCallback(async () => {
    setCargandoLista(true);
    try {
      setUsuarios(await usuariosApi.listar());
    } catch (e) {
      setError(e.message);
    } finally {
      setCargandoLista(false);
    }
  }, []);

  useEffect(() => { cargar(); }, [cargar]);

  async function guardar(event) {
    event.preventDefault();
    setGuardando(true);
    setError("");
    setAviso("");
    try {
      await usuariosApi.crear(form);
      setForm(null);
      setAviso("Cuenta creada. El empleado ya puede iniciar sesión.");
      await cargar();
    } catch (e) {
      setError(e.message);
    } finally {
      setGuardando(false);
    }
  }

  return (
    <section>
      <header className="encabezado">
        <div>
          <p className="sobretitulo">Administración</p>
          <h1>Usuarios y roles</h1>
          <p className="detalle">Crea una cuenta para cada integrante del personal y asígnale su rol.</p>
        </div>
        {!form && <button className="btn" onClick={() => { setError(""); setAviso(""); setForm({ ...FORM_VACIO }); }}>Nuevo usuario</button>}
      </header>
      {error && <p className="error" role="alert">{error}</p>}
      {aviso && <p className="aviso" role="status">{aviso}</p>}
      {form && (
        <form className="panel form usuario-form" onSubmit={guardar}>
          <h2>Crear usuario</h2>
          <div className="form-grid">
            <label>Nombre de usuario
              <input value={form.username} onChange={(e) => setForm({ ...form, username: e.target.value })} maxLength="150" autoComplete="off" required autoFocus />
            </label>
            <label>Rol
              <select value={form.rol} onChange={(e) => setForm({ ...form, rol: e.target.value })}>
                {ROLES.map(([valor, etiqueta]) => <option value={valor} key={valor}>{etiqueta}</option>)}
              </select>
            </label>
            <label>Nombre (opcional)
              <input value={form.first_name} onChange={(e) => setForm({ ...form, first_name: e.target.value })} maxLength="150" />
            </label>
            <label>Apellido (opcional)
              <input value={form.last_name} onChange={(e) => setForm({ ...form, last_name: e.target.value })} maxLength="150" />
            </label>
            <label>Correo electrónico (opcional)
              <input type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} maxLength="254" />
            </label>
            <label>Contraseña inicial
              <input type="password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} minLength="8" maxLength="128" required autoComplete="new-password" aria-describedby="ayuda-contrasena" />
            </label>
          </div>
          <p id="ayuda-contrasena" className="detalle">Usa al menos 8 caracteres. Comparte la contraseña inicial de forma privada.</p>
          {form.rol === "administrador" && <p className="detalle">Este rol administra DinoCafé; el acceso a Django Admin se asigna por separado.</p>}
          <div className="acciones">
            <button type="submit" className="btn" disabled={guardando}>{guardando ? "Guardando…" : "Crear cuenta"}</button>
            <button type="button" className="btn-texto" disabled={guardando} onClick={() => { setForm(null); setError(""); }}>Cancelar</button>
          </div>
        </form>
      )}
      <div className="tabla-scroll panel tabla-panel">
        <table>
          <thead><tr><th>Usuario</th><th>Nombre</th><th>Rol</th><th>Estado</th></tr></thead>
          <tbody>
            {usuarios.map((usuario) => (
              <tr key={usuario.id}>
                <td><strong>{usuario.username}</strong></td>
                <td>{[usuario.first_name, usuario.last_name].filter(Boolean).join(" ") || "—"}</td>
                <td>{ROLES.find(([rol]) => rol === usuario.rol)?.[1] ?? usuario.rol}</td>
                <td>{usuario.is_active ? "Activo" : "Inactivo"}</td>
              </tr>
            ))}
            {!usuarios.length && <tr><td colSpan="4" className="vacio">{cargandoLista ? "Cargando cuentas…" : error ? "No se pudo cargar la lista." : "No hay cuentas registradas."}</td></tr>}
          </tbody>
        </table>
      </div>
    </section>
  );
}
