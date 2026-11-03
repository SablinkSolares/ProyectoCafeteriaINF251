import { useCallback, useEffect, useState } from "react";
import { getRol, productosApi } from "../api";
import BuscadorProductos from "./BuscadorProductos";
import ProductoForm from "./ProductoForm";
import StockBadge from "./StockBadge";

// RF1 (S1-T04): gestión y consulta del catálogo. RF9 (S2-T08): buscador. RF4 (S2-T02): stock.
export default function Catalogo() {
  const esAdmin = getRol() === "administrador";
  const [categorias, setCategorias] = useState([]);
  const [productos, setProductos] = useState([]);
  const [busqueda, setBusqueda] = useState("");
  const [categoria, setCategoria] = useState("");
  const [editando, setEditando] = useState(null); // null | "nuevo" | producto
  const [estado, setEstado] = useState("cargando"); // cargando | listo | error
  const [error, setError] = useState("");
  const [errorCategorias, setErrorCategorias] = useState("");
  const [aviso, setAviso] = useState("");

  const alBuscar = useCallback((q) => setBusqueda(q), []);

  useEffect(() => {
    productosApi.categorias().then(setCategorias).catch((e) => setErrorCategorias(e.message));
  }, []);

  const cargar = useCallback(async () => {
    setEstado("cargando");
    try {
      setProductos(await productosApi.listar({ q: busqueda, categoria }));
      setError("");
      setEstado("listo");
    } catch (e) {
      setError(e.message);
      setEstado("error");
    }
  }, [busqueda, categoria]);

  useEffect(() => { cargar(); }, [cargar]);

  async function guardar(datos) {
    const esNuevo = editando === "nuevo";
    if (esNuevo) await productosApi.crear(datos);
    else await productosApi.actualizar(editando.id, datos);

    setEditando(null);
    setAviso(esNuevo ? "Producto agregado al catálogo." : "Producto actualizado.");

    // Si había un filtro activo, se limpia para que el cambio sea visible;
    // el efecto de carga se dispara solo con el cambio de filtros.
    if (busqueda || categoria) {
      setBusqueda("");
      setCategoria("");
    } else {
      await cargar();
    }
  }

  if (editando) {
    return (
      <ProductoForm
        categorias={categorias}
        puedeCambiarPrecio={esAdmin}
        producto={editando === "nuevo" ? null : editando}
        onGuardar={guardar}
        onCancelar={() => setEditando(null)}
      />
    );
  }

  const resumen = `${productos.length} producto${productos.length === 1 ? "" : "s"}`;

  return (
    <section>
      <header className="encabezado">
        <div>
          <h1>Catálogo</h1>
          {estado === "listo" && (
            <p className="detalle" aria-live="polite">
              {resumen}{busqueda ? ` para “${busqueda}”` : ""}{categoria ? " en la categoría elegida" : ""}
            </p>
          )}
        </div>
        {esAdmin && (
          <button className="btn" onClick={() => { setAviso(""); setEditando("nuevo"); }}>
            Agregar producto
          </button>
        )}
      </header>

      <BuscadorProductos onBuscar={alBuscar} />

      <div className="chips" role="group" aria-label="Filtrar por categoría">
        <button className={`chip ${categoria === "" ? "activo" : ""}`} onClick={() => setCategoria("")}>Todos</button>
        {categorias.map((c) => (
          <button key={c.id} className={`chip ${categoria === String(c.id) ? "activo" : ""}`}
            onClick={() => setCategoria(String(c.id))}>{c.nombre}</button>
        ))}
      </div>

      {aviso && <p className="aviso" role="status">{aviso}</p>}
      {errorCategorias && (
        <p className="error" role="alert">No se pudieron cargar las categorías: {errorCategorias}</p>
      )}
      {estado === "error" && (
        <p className="error" role="alert">No se pudo cargar el catálogo: {error}</p>
      )}
      {estado === "cargando" && <p className="vacio">Cargando productos…</p>}
      {estado === "listo" && productos.length === 0 && (
        <p className="vacio">
          {busqueda ? `No hay productos que coincidan con “${busqueda}”.` : "Aún no hay productos. Agrega el primero."}
        </p>
      )}

      <ul className="lista-productos">
        {productos.map((p) => (
          <li key={p.id} className="producto">
            <div>
              <h3>{p.nombre}</h3>
              <p className="detalle">{p.categoria_nombre}</p>
            </div>
            <div className="producto-derecha">
              <strong className="precio">Bs {p.precio}</strong>
              <StockBadge stock={p.stock} />
              {esAdmin && (
                <button className="btn-texto" onClick={() => { setAviso(""); setEditando(p); }}>
                  Editar
                </button>
              )}
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}
