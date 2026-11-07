import { useCallback, useEffect, useState } from "react";
import { inventarioApi } from "../api";

const VACIO = { nombre_insumo: "", unidad_medida: "g", cantidad_stock: "" };
export default function Inventario() {
  const [lista, setLista] = useState([]);
  const [form, setForm] = useState(VACIO);
  const [id, setId] = useState(null);
  const [error, setError] = useState("");
  const [aviso, setAviso] = useState("");
  const [ocupado, setOcupado] = useState(false);
  const cargar = useCallback(() => inventarioApi.listar().then(setLista).catch(e => setError(e.message)), []);
  useEffect(() => { cargar(); }, [cargar]);
  async function guardar(e) {
    e.preventDefault(); setOcupado(true); setError(""); setAviso("");
    try { if(id) await inventarioApi.actualizar(id,form); else await inventarioApi.crear(form); setForm(VACIO); setId(null); setAviso("Inventario actualizado."); await cargar(); }
    catch(err) { setError(err.message); }
    finally { setOcupado(false); }
  }
  const campo = nombre => e => setForm(f => ({ ...f, [nombre]: e.target.value }));
  return <section>
    <header className="encabezado"><div><p className="sobretitulo">Control de existencias</p><h1>Insumos e inventario</h1><p className="detalle">Registra ingredientes y sus existencias. Las recetas se editan en cada producto del catálogo.</p></div><button className="btn-secundario" onClick={cargar}>Actualizar</button></header>
    <form className="panel inventario-form" onSubmit={guardar}>
      <h2>{id ? "Editar insumo" : "Registrar insumo"}</h2>
      <div className="filtros-periodo"><label>Nombre del insumo<input value={form.nombre_insumo} onChange={campo("nombre_insumo")} maxLength={120} required /></label>
      <label>Unidad de medida<input value={form.unidad_medida} onChange={campo("unidad_medida")} placeholder="g, ml, unidad" maxLength={40} required /></label>
      <label>Stock físico<input type="number" min="0" step="0.001" value={form.cantidad_stock} onChange={campo("cantidad_stock")} required /></label>
      <button className="btn" disabled={ocupado}>{ocupado ? "Guardando…" : "Guardar insumo"}</button>
      {id && <button type="button" className="btn-texto" onClick={() => { setId(null); setForm(VACIO); }}>Cancelar edición</button>}</div>
    </form>
    {error && <p className="error" role="alert">{error}</p>}{aviso && <p className="aviso" role="status">{aviso}</p>}
    <div className="panel tabla-panel tabla-scroll"><table><thead><tr><th>Insumo</th><th>Unidad</th><th>Stock físico</th><th>Reservado</th><th>Disponible</th><th>Acciones</th></tr></thead>
      <tbody>{lista.map(n => <tr key={n.id}><td>{n.nombre_insumo}</td><td>{n.unidad_medida}</td><td>{n.cantidad_stock}</td><td>{n.reservado}</td><td><b>{n.disponible}</b></td><td><button className="btn-texto" onClick={() => { setId(n.id); setForm({ nombre_insumo:n.nombre_insumo,unidad_medida:n.unidad_medida,cantidad_stock:n.cantidad_stock }); }}>Editar {n.nombre_insumo}</button></td></tr>)}</tbody></table>
      {!lista.length && <p className="vacio">Aún no hay insumos registrados.</p>}
    </div>
  </section>;
}
