import { useState } from "react";

const PRECIO_VALIDO = /^\d+(\.\d{1,2})?$/; // decimal exacto, sin float (RNF7)

// RF1: alta y edición de producto. Solo el administrador cambia precios (RD1);
// el servidor vuelve a validarlo, aquí solo se bloquea el campo.
export default function ProductoForm({ categorias, producto, puedeCambiarPrecio, onGuardar, onCancelar }) {
  const [form, setForm] = useState({
    nombre: producto?.nombre ?? "",
    categoria: producto?.categoria ?? categorias[0]?.id ?? "",
    precio: producto?.precio ?? "",
    stock: producto?.stock ?? 0,
  });
  const [error, setError] = useState("");
  const [guardando, setGuardando] = useState(false);

  const cambiar = (campo) => (e) => setForm({ ...form, [campo]: e.target.value });
  const sinCategorias = categorias.length === 0;

  async function enviar(e) {
    e.preventDefault();
    if (!form.nombre.trim()) return setError("Escribe el nombre del producto.");
    if (!form.categoria) return setError("Selecciona una categoría.");
    const precio = String(form.precio).trim();
    if (!PRECIO_VALIDO.test(precio)) return setError("El precio debe ser un número con hasta 2 decimales, por ejemplo 7.50.");
    if (!Number.isInteger(Number(form.stock)) || Number(form.stock) < 0) return setError("El stock debe ser un número entero de 0 o más.");
    setError("");
    setGuardando(true);
    try {
      await onGuardar({
        ...form,
        nombre: form.nombre.trim(),
        categoria: Number(form.categoria),
        precio,
        stock: Number(form.stock),
      });
    } catch (err) {
      setError(err.message);
      setGuardando(false);
    }
  }

  return (
    <form className="panel form" onSubmit={enviar}>
      <h2>{producto ? "Editar producto" : "Nuevo producto"}</h2>
      {sinCategorias && (
        <p className="error" role="alert">
          No hay categorías registradas. Crea una desde el administrador de Django.
        </p>
      )}
      <label>Nombre
        <input value={form.nombre} onChange={cambiar("nombre")} autoFocus={!producto} />
      </label>
      <label>Categoría
        <select value={form.categoria} onChange={cambiar("categoria")} disabled={sinCategorias}>
          {sinCategorias && <option value="">Sin categorías</option>}
          {categorias.map((c) => <option key={c.id} value={c.id}>{c.nombre}</option>)}
        </select>
      </label>
      <label>Precio (Bs)
        <input inputMode="decimal" value={form.precio} onChange={cambiar("precio")}
          disabled={Boolean(producto) && !puedeCambiarPrecio} />
      </label>
      <label>Stock
        <input type="number" min="0" step="1" value={form.stock} onChange={cambiar("stock")} />
      </label>
      {error && <p className="error" role="alert">{error}</p>}
      <div className="acciones">
        <button type="submit" className="btn" disabled={guardando || sinCategorias}>Guardar producto</button>
        <button type="button" className="btn-texto" onClick={onCancelar}>Cancelar</button>
      </div>
    </form>
  );
}
