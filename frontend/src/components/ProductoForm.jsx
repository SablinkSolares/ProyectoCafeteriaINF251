import { useEffect, useState } from "react";
import { inventarioApi } from "../api";
import ImagenProducto from "./ImagenProducto";

export default function ProductoForm({ categorias, producto, puedeCambiarPrecio, onGuardar, onCancelar }) {
  const [form, setForm] = useState({
    nombre: producto?.nombre ?? "", categoria: producto?.categoria ?? categorias[0]?.id ?? "",
    precio: producto?.precio ?? "", stock: producto?.stock_fisico ?? producto?.stock ?? 0,
    imagen: producto?.imagen ?? "", preparable: producto?.preparable ?? false,
    insumos: producto?.insumos?.map(r => ({ insumo: r.insumo, cantidad_insumo_por_unidad: r.cantidad_insumo_por_unidad })) ?? [],
  });
  const [insumos, setInsumos] = useState([]);
  const [error, setError] = useState("");
  const [guardando, setGuardando] = useState(false);
  const [subiendo, setSubiendo] = useState(false);
  useEffect(() => { inventarioApi.listar().then(setInsumos).catch(e => setError(e.message)); }, []);
  const cambiar = campo => e => setForm(f => ({ ...f, [campo]: e.target.value }));
  function receta(indice, campo, valor) {
    setForm(f => ({ ...f, insumos: f.insumos.map((r,i) => i === indice ? { ...r, [campo]: valor } : r) }));
  }
  async function subir(e) {
    const archivo = e.target.files[0];
    if (!archivo) return;
    setSubiendo(true); setError("");
    try { const data = await inventarioApi.subirImagen(archivo); setForm(f => ({ ...f, imagen: data.imagen })); }
    catch (err) { setError(err.message); }
    finally { setSubiendo(false); }
  }
  async function enviar(e) {
    e.preventDefault();
    if (!form.nombre.trim()) return setError("Escribe el nombre del producto.");
    if (!form.categoria) return setError("Selecciona una categoría.");
    if (!/^\d+(\.\d{1,2})?$/.test(String(form.precio)) || Number(form.precio) <= 0) return setError("El precio debe ser positivo y tener hasta 2 decimales.");
    if (!form.preparable && (!Number.isInteger(Number(form.stock)) || Number(form.stock) < 0)) return setError("El stock debe ser un número entero de 0 o más.");
    if (!form.imagen.trim()) return setError("Debes agregar una imagen del producto.");
    if (form.preparable && (!form.insumos.length || form.insumos.some(r => !r.insumo || Number(r.cantidad_insumo_por_unidad) <= 0))) return setError("Completa los insumos y cantidades de la receta.");
    setGuardando(true); setError("");
    try {
      await onGuardar({ ...form, nombre: form.nombre.trim(), categoria: Number(form.categoria),
        stock: form.preparable ? 0 : Number(form.stock), imagen: form.imagen.trim(),
        insumos: form.preparable ? form.insumos.map(r => ({ ...r, insumo: Number(r.insumo) })) : [] });
    } catch (err) { setError(err.message); }
    finally { setGuardando(false); }
  }
  return <form className="panel form producto-form" onSubmit={enviar}>
    <p className="sobretitulo">Catálogo · Administración</p>
    <h2>{producto ? "Editar producto" : "Nuevo producto"}</h2>
    {!categorias.length && <p className="error" role="alert">No hay categorías registradas.</p>}
    <label>Nombre<input value={form.nombre} onChange={cambiar("nombre")} required maxLength={120} /></label>
    <div className="form-grid">
      <label>Categoría<select value={form.categoria} onChange={cambiar("categoria")} required>
        {!categorias.length && <option value="">Sin categorías</option>}
        {categorias.map(c => <option key={c.id} value={c.id}>{c.nombre}</option>)}
      </select></label>
      <label>Precio (Bs)<input inputMode="decimal" value={form.precio} onChange={cambiar("precio")} disabled={Boolean(producto) && !puedeCambiarPrecio} required /></label>
    </div>
    <label className="checkbox-label"><input type="checkbox" checked={form.preparable} onChange={e => setForm(f => ({ ...f, preparable: e.target.checked }))} />Se prepara con insumos</label>
    {!form.preparable ? <label>Stock<input type="number" min="0" step="1" value={form.stock} onChange={cambiar("stock")} required /></label> :
      <fieldset><legend>Receta por unidad</legend>
        <p className="detalle">La disponibilidad se calcula con los insumos libres de reservas.</p>
        {form.insumos.map((r,i) => <div className="receta-fila" key={i}>
          <label>Insumo<select value={r.insumo} onChange={e => receta(i,"insumo",e.target.value)} required><option value="">Seleccionar…</option>{insumos.map(n => <option key={n.id} value={n.id}>{n.nombre_insumo} ({n.unidad_medida})</option>)}</select></label>
          <label>Cantidad por unidad<input type="number" min="0.001" step="0.001" value={r.cantidad_insumo_por_unidad} onChange={e => receta(i,"cantidad_insumo_por_unidad",e.target.value)} required /></label>
          <button className="btn-texto" type="button" onClick={() => setForm(f => ({ ...f, insumos: f.insumos.filter((_,j) => j !== i) }))}>Quitar</button>
        </div>)}
        <button className="btn-secundario" type="button" onClick={() => setForm(f => ({ ...f, insumos: [...f.insumos, { insumo: "", cantidad_insumo_por_unidad: "" }] }))}>Agregar insumo</button>
      </fieldset>}
    <label>Imagen del producto (obligatoria)<input type="file" accept="image/png,image/jpeg,image/webp" onChange={subir} disabled={subiendo} /></label>
    <label>Ruta o URL de imagen<input value={form.imagen} onChange={cambiar("imagen")} placeholder="/images/productos/cafe.jpg" required /></label>
    {form.imagen && <ImagenProducto src={form.imagen} nombre={form.nombre || "Vista previa"} />}
    {subiendo && <p role="status">Subiendo imagen…</p>}
    {error && <p className="error" role="alert">{error}</p>}
    <div className="acciones"><button className="btn" disabled={guardando || subiendo || !categorias.length}>{guardando ? "Guardando…" : "Guardar producto"}</button><button type="button" className="btn-texto" onClick={onCancelar}>Cancelar</button></div>
  </form>;
}
