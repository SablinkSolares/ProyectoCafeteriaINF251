import { useCallback, useEffect, useState } from "react";
import { pedidosApi } from "../api";

const ESTADOS = [
  ["ESPERA", "En espera"],
  ["EN_PREPARACION", "En preparación"],
  ["LISTO", "Listo para entregar"],
  ["ENTREGADO", "Entregado"],
];

function moneda(valor) {
  return new Intl.NumberFormat("es-BO", { style: "currency", currency: "BOB" }).format(Number(valor));
}

function fecha(valor) {
  if (!valor) return "Pendiente";
  return new Date(valor).toLocaleString("es-BO", { dateStyle: "short", timeStyle: "short" });
}

export default function SeguimientoPedidos() {
  const [pedidos, setPedidos] = useState([]);
  const [filtro, setFiltro] = useState("TODOS");
  const [error, setError] = useState("");
  const [actualizado, setActualizado] = useState(null);

  const cargar = useCallback(async () => {
    try {
      setPedidos(await pedidosApi.listarAdministrador());
      setActualizado(new Date());
      setError("");
    } catch (e) {
      setError(e.message);
    }
  }, []);

  useEffect(() => {
    cargar();
    const timer = setInterval(cargar, 4000);
    return () => clearInterval(timer);
  }, [cargar]);

  const visibles = pedidos.filter((pedido) => filtro === "TODOS" || pedido.estado === filtro);
  const totalPorEstado = (estado) => pedidos.filter((pedido) => pedido.estado === estado).length;

  return (
    <section>
      <header className="encabezado">
        <div>
          <p className="sobretitulo">Supervisión general</p>
          <h1>Seguimiento de pedidos</h1>
          <p className="detalle">Administración puede observar todo el recorrido: registro, cobro, cocina y entrega.</p>
          {actualizado && <p className="detalle">Actualizado {actualizado.toLocaleTimeString("es-BO")} · actualización automática cada 4 segundos.</p>}
        </div>
        <button className="btn-secundario" onClick={cargar}>Actualizar</button>
      </header>

      <div className="resumen-ventas seguimiento-resumen">
        <article className="indicador"><span>Total de pedidos</span><strong>{pedidos.length}</strong></article>
        <article className="indicador"><span>Sin pago registrado</span><strong>{pedidos.filter((pedido) => !pedido.pago).length}</strong></article>
        <article className="indicador"><span>En cocina</span><strong>{totalPorEstado("ESPERA") + totalPorEstado("EN_PREPARACION")}</strong></article>
        <article className="indicador indicador-destacado"><span>Listos para entregar</span><strong>{totalPorEstado("LISTO")}</strong></article>
      </div>

      <div className="chips" role="group" aria-label="Filtrar seguimiento por estado">
        <button className={`chip ${filtro === "TODOS" ? "activo" : ""}`} onClick={() => setFiltro("TODOS")}>Todos</button>
        {ESTADOS.map(([valor, etiqueta]) => (
          <button key={valor} className={`chip ${filtro === valor ? "activo" : ""}`} onClick={() => setFiltro(valor)}>{etiqueta}</button>
        ))}
      </div>
      {error && <p className="error" role="alert">{error}</p>}
      {visibles.length === 0 && !error && <p className="vacio">No hay pedidos para este filtro.</p>}

      <div className="lista-operaciones">
        {visibles.map((pedido) => (
          <article className="pedido-operacion seguimiento-card" key={pedido.id}>
            <header className="pedido-operacion-cabecera">
              <div><p className="sobretitulo">Mesa no registrada</p><h2>Pedido #{pedido.id}</h2></div>
              <span className={`estado-pedido estado-${pedido.estado.toLowerCase()}`}>{ESTADOS.find(([valor]) => valor === pedido.estado)?.[1] || pedido.estado}</span>
            </header>
            <ul className="lineas-pedido">
              {pedido.detalles.map((detalle) => (
                <li key={detalle.id}><span>{detalle.cantidad}× {detalle.producto}</span><strong>{moneda(detalle.subtotal)}</strong></li>
              ))}
            </ul>
            <div className="seguimiento-datos">
              <p><span>Registrado por</span><b>No disponible</b></p>
              <p><span>Pago</span><b>{!pedido.pago ? "Sin registrar" : `${pedido.pago.metodo} · ${pedido.pago.estado}`}</b></p>
              <p><span>Responsables de preparación y entrega</span><b>No disponibles</b></p>
            </div>
            <div className="seguimiento-fechas">
              <span>Registrado: {fecha(pedido.creado_en)}</span>
              <span>Fechas de cambios de estado: no disponibles</span>
            </div>
            <footer className="pedido-operacion-pie"><span className="detalle">Total del pedido</span><strong>{moneda(pedido.total)}</strong></footer>
          </article>
        ))}
      </div>
    </section>
  );
}
