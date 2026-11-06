import { useCallback, useEffect, useRef, useState } from "react";
import { pedidosApi } from "../api";
import { NuevoPedidoCaja } from "./VistaCaja";

export default function VistaMesero() {
  const [pedidos, setPedidos] = useState([]);
  const [error, setError] = useState("");
  const [ocupado, setOcupado] = useState(null);
  const [notificacion, setNotificacion] = useState("");
  const idsAnteriores = useRef(null);

  const cargar = useCallback(async () => {
    try {
      const nuevos = await pedidosApi.listarMesero();
      const idsActuales = nuevos.map((pedido) => pedido.id);
      const llegadas = idsAnteriores.current === null
        ? nuevos
        : nuevos.filter((pedido) => !idsAnteriores.current.includes(pedido.id));
      if (llegadas.length) {
        const primero = llegadas[0];
        setNotificacion(`${llegadas.length} pedido${llegadas.length > 1 ? "s" : ""} listo${llegadas.length > 1 ? "s" : ""}. ${primero ? `Pedido #${primero.id}.` : ""}`);
        // Notificación del navegador si el usuario ya concedió permiso; no se solicita sin acción.
        if (typeof Notification !== "undefined" && Notification.permission === "granted") {
          llegadas.forEach((pedido) => new Notification("DinoCafé · Pedido listo", {
            body: `Pedido #${pedido.id}. Ya puedes llevarlo.`,
          }));
        }
      }
      idsAnteriores.current = idsActuales;
      setPedidos(nuevos);
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

  async function registrarEntrega(pedido) {
    setOcupado(pedido.id);
    try {
      await pedidosApi.cambiarEstado(pedido.id, "ENTREGADO");
      setPedidos((actuales) => actuales.filter((p) => p.id !== pedido.id));
      setNotificacion(`Pedido #${pedido.id} marcado como entregado.`);
      setError("");
    } catch (e) {
      setError(e.message);
    } finally {
      setOcupado(null);
    }
  }

  return (
    <section>
      <header className="encabezado">
        <div>
          <p className="sobretitulo">Atención</p>
          <h1>Entregas</h1>
          <p className="detalle">Aquí solo confirmas la entrega de los pedidos que cocina marcó como listos.</p>
        </div>
        <button className="btn-secundario" onClick={cargar}>Actualizar</button>
      </header>
      <NuevoPedidoCaja alCrear={cargar} puedeCrear />
      {notificacion && <div className="notificacion-pedido" role="status"><b>Notificación</b><span>{notificacion}</span></div>}
      {error && <p className="error" role="alert">{error}</p>}
      {pedidos.length === 0 && !error && <p className="vacio">No hay pedidos listos para entregar.</p>}
      <div className="lista-operaciones">
        {pedidos.map((pedido) => (
          <article className="pedido-operacion" key={pedido.id}>
            <header className="pedido-operacion-cabecera">
              <div><p className="sobretitulo">Pedido</p><h2>#{pedido.id}</h2></div>
              <span className="estado-pedido estado-listo">Listo para entregar</span>
            </header>
            <ul className="lineas-pedido">
              {pedido.detalles.map((detalle) => (
                <li key={detalle.id}><span><b>{detalle.cantidad}×</b> {detalle.producto}</span><strong>{new Intl.NumberFormat("es-BO", { style: "currency", currency: "BOB" }).format(Number(detalle.subtotal))}</strong></li>
              ))}
            </ul>
            <footer className="pedido-operacion-pie">
              <strong>{new Intl.NumberFormat("es-BO", { style: "currency", currency: "BOB" }).format(Number(pedido.total))}</strong>
              <button className="btn" disabled={ocupado === pedido.id} onClick={() => registrarEntrega(pedido)}>
                {ocupado === pedido.id ? "Guardando…" : "Confirmar entrega"}
              </button>
            </footer>
          </article>
        ))}
      </div>
    </section>
  );
}
