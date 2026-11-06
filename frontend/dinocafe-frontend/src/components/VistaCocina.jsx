import { useCallback, useEffect, useRef, useState } from "react";
import { pedidosApi } from "../api";

// RF3 / RF5 (S1-T08): cocina recibe pedidos y avanza su estado. "Entregado" lo registra el mesero.
const COLUMNAS = [
  { estado: "ESPERA", titulo: "En espera", accion: "Empezar a preparar", siguiente: "EN_PREPARACION" },
  { estado: "EN_PREPARACION", titulo: "En preparación", accion: "Marcar como listo", siguiente: "LISTO" },
  { estado: "LISTO", titulo: "Listos para entregar", accion: null, siguiente: null },
];
const REFRESCO_MS = 4000; // sondeo simple para ver pedidos pagados sin recargar

function minutosDesde(fecha) {
  return Math.max(0, Math.floor((Date.now() - new Date(fecha).getTime()) / 60000));
}

export default function VistaCocina() {
  const [pedidos, setPedidos] = useState([]);
  const [error, setError] = useState("");
  const [ocupado, setOcupado] = useState(null); // id del pedido que se está actualizando
  const [actualizado, setActualizado] = useState(null);
  const enCurso = useRef(false); // evita que dos sondeos se superpongan

  const cargar = useCallback(async () => {
    if (enCurso.current) return;
    enCurso.current = true;
    try {
      setPedidos(await pedidosApi.listarCocina());
      setError("");
      setActualizado(new Date());
    } catch (e) {
      setError(e.message);
    } finally {
      enCurso.current = false;
    }
  }, []);

  useEffect(() => {
    cargar();
    const intervalo = setInterval(cargar, REFRESCO_MS);
    return () => clearInterval(intervalo);
  }, [cargar]);

  async function avanzar(pedido, siguiente) {
    setOcupado(pedido.id);
    try {
      // El servidor devuelve el pedido actualizado; se refleja al instante.
      const actualizadoPedido = await pedidosApi.cambiarEstado(pedido.id, siguiente);
      setPedidos((prev) => prev.map((p) => (p.id === actualizadoPedido.id ? actualizadoPedido : p)));
      setError("");
      setActualizado(new Date());
    } catch (e) {
      setError(e.message); // p. ej. transición inválida rechazada por el servidor
    } finally {
      setOcupado(null);
    }
  }

  return (
    <section>
      <header className="encabezado">
        <h1>Cocina</h1>
        {actualizado && (
          <p className="detalle" aria-live="polite">
            Pedidos por estado · actualizado {actualizado.toLocaleTimeString("es-BO")}
          </p>
        )}
      </header>
      {error && <p className="error" role="alert">{error}</p>}
      <div className="tablero">
        {COLUMNAS.map((col) => {
          const lista = pedidos.filter((p) => p.estado === col.estado)
            .sort((a, b) => new Date(a.creado_en) - new Date(b.creado_en)); // orden de llegada
          return (
            <div key={col.estado} className="columna">
              <h2>{col.titulo} <span className="contador">{lista.length}</span></h2>
              {lista.length === 0 && <p className="vacio">Sin pedidos.</p>}
              {lista.map((p) => {
                const unidades = p.detalles.reduce((suma, d) => suma + d.cantidad, 0);
                return (
                  <article key={p.id} className="ticket">
                    <header>
                      <strong className="numero">#{p.id}</strong>
                      <span className="detalle">
                        {unidades} ítem{unidades === 1 ? "" : "s"} · hace {minutosDesde(p.creado_en)} min
                      </span>
                    </header>
                    <ul>
                      {p.detalles.map((d) => (
                        <li key={d.id}>
                          <span><b>{d.cantidad}×</b> {d.producto}</span>
                        </li>
                      ))}
                    </ul>
                    {col.accion && (
                      <button
                        className="btn"
                        disabled={ocupado === p.id}
                        onClick={() => avanzar(p, col.siguiente)}
                        aria-label={`${col.accion} del pedido ${p.id}`}
                      >
                        {col.accion}
                      </button>
                    )}
                  </article>
                );
              })}
            </div>
          );
        })}
      </div>
    </section>
  );
}
