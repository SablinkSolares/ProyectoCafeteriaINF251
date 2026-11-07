import { useEffect, useState } from "react";
import { pedidosApi } from "../api";
import { ESTADOS, moneda, fechaHora } from "../utils";

export function DatosPedido({ pedido: p }) {
  return <>
    <div className="seguimiento-datos"><p><span>Mesa</span><b>{p.mesa}</b></p><p><span>Registrado por</span><b>{p.registrado_por_nombre || "Sin registro histórico"}</b></p><p><span>Pago</span><b>{p.pago?.estado || "Sin registrar"}</b></p><p><span>Observaciones</span><b>{p.observaciones || "Sin observaciones"}</b></p></div>
    <ol className="historial-pedido">{[["Registro",p.creado_en,p.registrado_por_nombre],["Pago confirmado",p.pago?.pagado_en,p.pago?.verificado_por_nombre],["En preparación",p.en_preparacion_en,p.preparado_por_nombre],["Listo",p.listo_en,p.listo_por_nombre],["Entregado",p.entregado_en,p.entregado_por_nombre],["Cancelado",p.cancelado_en,p.motivo_cancelacion]].map(([nombre,fecha,persona]) => <li key={nombre}><b>{nombre}</b><span>{fechaHora(fecha)}</span>{persona && <small>{persona}</small>}</li>)}</ol>
    {p.pedido_original && <p>Reemplaza al pedido <a href={`#pedido/${p.pedido_original}`}>#{p.pedido_original}</a> · {p.motivo_cambio}</p>}
    {p.reemplazos?.map(id => <p key={id}>Reemplazado por <a href={`#pedido/${id}`}>pedido #{id}</a></p>)}
  </>;
}
export default function DetallePedido({ id }) {
  const [pedido, setPedido] = useState(null);
  const [error, setError] = useState("");
  useEffect(() => { let activa=true; pedidosApi.obtener(id).then(p => {if(activa) setPedido(p);}).catch(e => {if(activa) setError(e.message);}); return () => {activa=false;}; }, [id]);
  return <section><header className="encabezado"><div><p className="sobretitulo">Detalle y trazabilidad</p><h1>Pedido #{id}</h1></div><a className="btn-secundario" href="#seguimiento">Volver al seguimiento</a></header>
    {error && <p className="error" role="alert">{error}</p>}
    {pedido && <article className="panel detalle-pedido"><span className="estado-pedido">{ESTADOS[pedido.estado]}</span><DatosPedido pedido={pedido} /><ul className="lineas-pedido">{pedido.detalles.map(d => <li key={d.id}><span>{d.cantidad}× {d.producto} · {moneda(d.precio_unitario)} c/u</span><strong>{moneda(d.subtotal)}</strong></li>)}</ul><p className="carrito-total">Total <strong>{moneda(pedido.total)}</strong></p></article>}
  </section>;
}
