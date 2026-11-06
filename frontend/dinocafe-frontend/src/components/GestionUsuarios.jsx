import { useCallback, useState } from "react";
import { getUsuario, usuariosApi } from "../api";

const ROLES = [
  ["administrador", "Administrador"],
  ["mesero", "Mesero"],
  ["cajero", "Cajero"],
  ["cocina", "Personal de cocina"],
];
const FORM_VACIO = { username: "", first_name: "", last_name: "", email: "", rol: "mesero", password: "" };

export default function GestionUsuarios() {
  const usuarioActual = getUsuario();
  const [usuarios, setUsuarios] = useState([]);
  const [form, setForm] = useState(null);
  const [cargando, setCargando] = useState(false);
  const [error, setError] = useState("");
  const [aviso, setAviso] = useState("");

  const cargar = useCallback(async () => {
    try {
      setUsuarios(await usuariosApi.listar());
      setError("");
    } catch (e) {
      setError(e.message);
    }
  }, []);

  // La API actual no publica gestión de cuentas; no se muestran datos ficticios.

  function editar(usuario) {
    setAviso("");
    setForm({ ...usuario, password: "" });
  }

  async function guardar(event) {
    event.preventDefault();
    setCargando(true);
    setError("");
    try {
      const datos = { ...form };
      if (!datos.password) delete datos.password;
      if (form.id) await usuariosApi.actualizar(form.id, datos);
      else await usuariosApi.crear(datos);
      setForm(null);
      setAviso(form.id ? "Usuario actualizado." : "Usuario creado.");
      await cargar();
    } catch (e) {
      setError(e.message);
    } finally {
      setCargando(false);
    }
  }

  async function alternar(usuario) {
    try {
      await usuariosApi.actualizar(usuario.id, { is_active: !usuario.is_active });
      setAviso(usuario.is_active ? "Cuenta desactivada." : "Cuenta activada.");
      await cargar();
    } catch (e) {
      setError(e.message);
    }
  }

  return (
    <section>
      <header className="encabezado">
        <div>
          <p className="sobretitulo">Administración</p>
          <h1>Usuarios y roles</h1>
          <p className="detalle">Crea cuentas, asigna responsabilidades y activa o desactiva accesos.</p>
        </div>
        {!form && <button className="btn" disabled title="Esta función aún no está disponible" onClick={() => { setError(""); setForm({ ...FORM_VACIO }); }}>Nuevo usuario</button>}
      </header>
      <p className="detalle" role="status">La gestión de usuarios no está disponible en el servidor actual.</p>
      {error && <p className="error" role="alert">{error}</p>}
      {aviso && <p className="aviso" role="status">{aviso}</p>}
      {form && (
        <form className="panel form usuario-form" onSubmit={guardar}>
          <h2>{form.id ? "Editar usuario" : "Crear usuario"}</h2>
          <div className="form-grid">
            <label>Nombre de usuario
              <input value={form.username} onChange={(e) => setForm({ ...form, username: e.target.value })} required disabled={Boolean(form.id)} autoFocus />
            </label>
            <label>Rol
              <select value={form.rol} onChange={(e) => setForm({ ...form, rol: e.target.value })}
                disabled={Boolean(form.id && form.username === usuarioActual)}>
                {ROLES.map(([valor, etiqueta]) => <option value={valor} key={valor}>{etiqueta}</option>)}
              </select>
            </label>
            <label>Nombre
              <input value={form.first_name} onChange={(e) => setForm({ ...form, first_name: e.target.value })} />
            </label>
            <label>Apellido
              <input value={form.last_name} onChange={(e) => setForm({ ...form, last_name: e.target.value })} />
            </label>
            <label>Correo electrónico
              <input type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
            </label>
            <label>{form.id ? "Nueva contraseña (opcional)" : "Contraseña"}
              <input type="password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} required={!form.id} autoComplete="new-password" />
            </label>
          </div>
          {form.id && <label className="checkbox-label"><input type="checkbox" checked={form.is_active}
            onChange={(e) => setForm({ ...form, is_active: e.target.checked })}
            disabled={form.username === usuarioActual} /> Cuenta activa</label>}
          <div className="acciones">
            <button type="submit" className="btn" disabled={cargando}>{cargando ? "Guardando…" : "Guardar usuario"}</button>
            <button type="button" className="btn-texto" onClick={() => setForm(null)}>Cancelar</button>
          </div>
        </form>
      )}
      <div className="tabla-scroll panel tabla-panel">
        <table>
          <thead><tr><th>Usuario</th><th>Nombre</th><th>Rol</th><th>Estado</th><th>Acciones</th></tr></thead>
          <tbody>
            {usuarios.map((usuario) => (
              <tr key={usuario.id}>
                <td><strong>{usuario.username}</strong></td>
                <td>{[usuario.first_name, usuario.last_name].filter(Boolean).join(" ") || "—"}</td>
                <td>{ROLES.find(([rol]) => rol === usuario.rol)?.[1] ?? usuario.rol}</td>
                <td><span className={`estado-cuenta ${usuario.is_active ? "cuenta-activa" : "cuenta-inactiva"}`}>{usuario.is_active ? "Activo" : "Inactivo"}</span></td>
                <td><div className="acciones-tabla">
                  <button className="btn-texto" onClick={() => editar(usuario)}>Editar</button>
                  <button className="btn-texto" onClick={() => alternar(usuario)} disabled={usuario.username === usuarioActual && usuario.is_active}>
                    {usuario.is_active ? "Desactivar" : "Activar"}
                  </button>
                </div></td>
              </tr>
            ))}
            {usuarios.length === 0 && <tr><td colSpan="5" className="vacio">No se puede consultar la lista de usuarios desde esta interfaz.</td></tr>}
          </tbody>
        </table>
      </div>
    </section>
  );
}
