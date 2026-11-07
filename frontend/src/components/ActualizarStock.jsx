import { useState } from "react";
import { productosApi } from "../api";

export default function ActualizarStock({ producto, onActualizado, onCancelar }) {
  const anterior = Number(producto.stock_fisico ?? producto.stock);
  const [cantidad, setCantidad] = useState(String(anterior));
  const [guardando, setGuardando] = useState(false);
  const [error, setError] = useState("");

  async function guardar(event) {
    event.preventDefault();
    if (!/^\d+$/.test(cantidad) || Number(cantidad) > 999999999) {
      setError("Introduce una cantidad entera entre 0 y 999999999.");
      return;
    }
    setGuardando(true);
    setError("");
    try {
      await productosApi.actualizarStock(producto.id, Number(cantidad), anterior);
      await onActualizado(producto.nombre);
    } catch (err) {
      setError(err.message);
    } finally {
      setGuardando(false);
    }
  }

  return <form className="panel stock-form" onSubmit={guardar} aria-labelledby="titulo-actualizar-stock">
    <div><p className="sobretitulo">Inventario de productos</p><h2 id="titulo-actualizar-stock">Actualizar stock de {producto.nombre}</h2>
      <p className="detalle">Stock registrado: <strong>{anterior} unidades</strong>. Indica las unidades disponibles para nuevos pedidos.</p>
      {producto.activo === false && <p className="detalle">El producto seguirá desactivado hasta que lo reactives.</p>}
    </div>
    <label>Nuevo stock disponible<input type="number" min="0" max="999999999" step="1" value={cantidad} onChange={event => setCantidad(event.target.value)} required autoFocus /></label>
    <div className="acciones"><button type="submit" className="btn" disabled={guardando}>{guardando ? "Guardando…" : "Guardar stock"}</button><button type="button" className="btn-texto" disabled={guardando} onClick={onCancelar}>Cancelar</button></div>
    {error && <p className="error" role="alert">{error}</p>}
  </form>;
}
