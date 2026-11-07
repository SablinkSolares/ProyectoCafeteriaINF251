import { useCallback, useEffect, useState } from "react";
import { pedidosApi } from "../api";
import { DatosPedido } from "./DetallePedido";
import { ESTADOS, moneda, fechaLocal } from "../utils";

export default function SeguimientoPedidos() {
  const [pedidos, setPedidos] = useState([]);
  const [dia, setDia] = useState(fechaLocal);
  const [filtro, setFiltro] = useState("TODOS");
  const [error, setError] = useState("");
  const [actualizado, setActualizado] = useState(null);
  const cargar = useCallback(async () => {
    try { setPedidos(await pedidosApi.listarAdministrador(dia)); setActualizado(new Date()); setError(""); }
    catch(e) { setError(e.message); }
  }, [dia]);
  useEffect(() => { cargar(); const timer = setInterval(cargar,4000); return () => clearInterval(timer); }, [cargar]);
  const visibles = pedidos.filter(p => filtro === "TODOS" || p.estado === filtro);
  return <section>
    <header className="encabezado"><div><p className="sobretitulo">Supervisión diaria</p><h1>Seguimiento de pedidos</h1><p className="detalle">Registro → preparación → entrega → cobro.</p>{actualizado && <p className="detalle">Actualizado {actualizado.toLocaleTimeString("es-BO")}</p>}</div><button className="btn-secundario" onClick={cargar}>Actualizar</button></header>
    <div className="filtros-periodo"><label>Día de seguimiento<input type="date" value={dia} onChange={e => setDia(e.target.value)} required /></label><button className="btn-secundario" onClick={() => setDia(fechaLocal())}>Hoy</button></div>
    <div className="resumen-ventas">
      <article className="indicador"><span>Pedidos del día</span><strong>{pedidos.length}</strong></article>
      <article className="indicador"><span>Por cobrar</span><strong>{pedidos.filter(p => p.estado === "ENTREGADO" && !p.pago).length}</strong></article>
      <article className="indicador"><span>En cocina</span><strong>{pedidos.filter(p => ["ESPERA","EN_PREPARACION"].includes(p.estado)).length}</strong></article>
      <article className="indicador indicador-destacado"><span>Pagos realizados</span><strong>{pedidos.filter(p => p.pago?.estado === "COMPLETADO").length}</strong></article>
    </div>
    <div className="chips" role="group" aria-label="Filtrar seguimiento por estado">{[["TODOS","Todos"], ...Object.entries(ESTADOS)].map(([id,nombre]) => <button key={id} className={`chip ${filtro === id ? "activo" : ""}`} onClick={() => setFiltro(id)}>{nombre}</button>)}</div>
    {error && <p className="error" role="alert">{error}</p>}
    {!visibles.length && !error && <p className="vacio">No hay pedidos para este día y estado.</p>}
    <div className="lista-operaciones">{visibles.map(p => <article className="pedido-operacion" key={p.id}>
      <header className="pedido-operacion-cabecera"><h2><a href={`#pedido/${p.id}`}>Pedido #{p.id}</a></h2><span className={`estado-pedido estado-${p.estado.toLowerCase()}`}>{ESTADOS[p.estado]}</span></header>
      <ul className="lineas-pedido">{p.detalles.map(d => <li key={d.id}><span>{d.cantidad}× {d.producto}</span><strong>{moneda(d.subtotal)}</strong></li>)}</ul>
      <DatosPedido pedido={p} />
      <footer className="pedido-operacion-pie"><span>Total</span><strong>{moneda(p.total)}</strong></footer>
    </article>)}</div>
  </section>;
}
