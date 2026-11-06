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
      const listos = nuevos.filter((pedido) => pedido.estado === "LISTO");
      const idsActuales = listos.map((pedido) => pedido.id);
      const llegadas = idsAnteriores.current === null
        ? listos
        : listos.filter((pedido) => !idsAnteriores.current.includes(pedido.id));
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

  async function cancelarPedido(pedido) {
    const aviso = pedido.estado === "ESPERA" ? "" : " Si ya se usaron productos o insumos, revisa el inventario físico.";
    if (!window.confirm(`¿Cancelar el pedido #${pedido.id} y liberar sus reservas?${aviso}`)) return;
    setOcupado(pedido.id);
    try {
      await pedidosApi.cancelar(pedido.id);
      setNotificacion(`Pedido #${pedido.id} cancelado y reservas liberadas.`);
      await cargar();
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
          <p className="detalle">Registra pedidos, consulta su preparación y confirma su entrega cuando estén listos.</p>
        </div>
        <button className="btn-secundario" onClick={cargar}>Actualizar</button>
      </header>
      <NuevoPedidoCaja alCrear={cargar} puedeCrear />
      {notificacion && <div className="notificacion-pedido" role="status"><b>Notificación</b><span>{notificacion}</span></div>}
      {error && <p className="error" role="alert">{error}</p>}
      {pedidos.length === 0 && !error && <p className="vacio">No hay pedidos activos.</p>}
      <div className="lista-operaciones">
        {pedidos.map((pedido) => (
          <article className="pedido-operacion" key={pedido.id}>
            <header className="pedido-operacion-cabecera">
              <div><p className="sobretitulo">Pedido</p><h2>#{pedido.id}</h2></div>
              <span className="estado-pedido estado-listo">{{ ESPERA: "En espera", EN_PREPARACION: "En preparación", LISTO: "Listo para entregar" }[pedido.estado]}</span>
            </header>
            <ul className="lineas-pedido">
              {pedido.detalles.map((detalle) => (
                <li key={detalle.id}><span><b>{detalle.cantidad}×</b> {detalle.producto}</span><strong>{new Intl.NumberFormat("es-BO", { style: "currency", currency: "BOB" }).format(Number(detalle.subtotal))}</strong></li>
              ))}
            </ul>
            <footer className="pedido-operacion-pie">
              <strong>{new Intl.NumberFormat("es-BO", { style: "currency", currency: "BOB" }).format(Number(pedido.total))}</strong>
              {pedido.estado === "LISTO" && <button className="btn" disabled={ocupado === pedido.id} onClick={() => registrarEntrega(pedido)}>
                {ocupado === pedido.id ? "Guardando…" : "Confirmar entrega"}
              </button>}
              {pedido.reserva_registrada && <button className="btn-secundario" disabled={ocupado === pedido.id} onClick={() => cancelarPedido(pedido)}>Cancelar pedido</button>}
              {!pedido.reserva_registrada && <span className="detalle">Pedido anterior: requiere revisión manual para cancelar.</span>}
            </footer>
          </article>
        ))}
      </div>
    </section>
  );
}
