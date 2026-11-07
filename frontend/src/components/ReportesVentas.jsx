import { useEffect, useState } from "react";
import { getRol, reportesApi } from "../api";
import { moneda, fechaLocal, fechaHora } from "../utils";

function Totales({ datos }) {
  return <div className="resumen-ventas">
    <article className="indicador"><span>Ventas brutas</span><strong>{moneda(datos.total_ventas)}</strong></article>
    <article className="indicador"><span>Reembolsos</span><strong>{moneda(datos.total_reembolsos)}</strong></article>
    <article className="indicador indicador-destacado"><span>Ventas netas</span><strong>{moneda(datos.total_neto)}</strong></article>
    <article className="indicador"><span>Pagos confirmados</span><strong>{datos.cantidad_pagos}</strong></article>
  </div>;
}
function PorMetodo({ datos }) {
  return <div className="panel tabla-panel tabla-scroll"><table><thead><tr><th>Método</th><th>Pagos</th><th>Ventas</th><th>Reembolsos</th><th>Neto</th></tr></thead><tbody>{Object.entries(datos.por_metodo).map(([m,d]) => <tr key={m}><td>{m === "qr" ? "Yape · QR" : "Efectivo"}</td><td>{d.cantidad}</td><td>{moneda(d.ventas)}</td><td>{moneda(d.reembolsos)}</td><td>{moneda(d.neto)}</td></tr>)}</tbody></table></div>;
}
export default function ReportesVentas() {
  const admin = getRol() === "administrador";
  const hoy = fechaLocal();
  const [desde, setDesde] = useState(hoy), [hasta, setHasta] = useState(hoy);
  const [fecha, setFecha] = useState(hoy), [efectivo, setEfectivo] = useState(""), [qr, setQr] = useState("");
  const [periodo, setPeriodo] = useState(null), [conciliacion, setConciliacion] = useState(null);
  const [historial, setHistorial] = useState([]);
  const [histDesde, setHistDesde] = useState(hoy), [histHasta, setHistHasta] = useState(hoy);
  const [ocupado, setOcupado] = useState(false), [error, setError] = useState(""), [aviso, setAviso] = useState("");
  async function ejecutar(fn) {
    setOcupado(true); setError(""); setAviso("");
    try { await fn(); } catch(e) { setError(e.message); } finally { setOcupado(false); }
  }
  async function cargarHistorial() { setHistorial(await reportesApi.historial(histDesde,histHasta)); }
  useEffect(() => { reportesApi.historial(hoy,hoy).then(setHistorial).catch(e => setError(e.message)); }, [hoy]);
  async function generar(tipo) {
    const datos = tipo === "CONCILIACION" ? { tipo, fecha, efectivo_real:efectivo, qr_real:qr } :
      tipo === "HISTORIAL" ? { tipo, desde:histDesde, hasta:histHasta } : { tipo, desde, hasta };
    const reporte = await reportesApi.generar(datos);
    await reportesApi.descargar(reporte.id);
    setAviso(`PDF #${reporte.id} generado y guardado en el historial.`);
    await cargarHistorial();
  }
  return <section>
    <header className="encabezado"><div><p className="sobretitulo">Control de caja</p><h1>Ventas y reportes</h1><p className="detalle">Consulta ventas, concilia efectivo y Yape, y descarga reportes PDF.</p></div></header>
    {error && <p className="error" role="alert">{error}</p>}{aviso && <p className="aviso" role="status">{aviso}</p>}
    <section className="seccion-reporte"><h2>Ventas por período</h2>
      <form className="filtros-periodo" onSubmit={e => { e.preventDefault(); ejecutar(async () => setPeriodo(await reportesApi.ventas(desde,hasta))); }}>
        <label>Desde<input type="date" value={desde} onChange={e => setDesde(e.target.value)} disabled={!admin} required /></label>
        <label>Hasta<input type="date" value={hasta} onChange={e => setHasta(e.target.value)} disabled={!admin} required /></label>
        <button className="btn" disabled={ocupado}>Consultar período</button>
        <button className="btn-secundario" type="button" disabled={ocupado || desde > hasta} onClick={() => ejecutar(() => generar("VENTAS"))}>Descargar ventas PDF</button>
      </form>
      {periodo && <><Totales datos={periodo} /><PorMetodo datos={periodo} />
        <div className="reportes-grid"><div className="panel tabla-panel tabla-scroll"><h2>Ventas por producto</h2><table><thead><tr><th>Producto</th><th>Unidades</th><th>Total bruto</th></tr></thead><tbody>{periodo.productos.map(p => <tr key={p.producto_id}><td>{p.producto__nombre}</td><td>{p.unidades}</td><td>{moneda(p.total)}</td></tr>)}</tbody></table>{!periodo.productos.length && <p className="detalle">No hay ventas en este período.</p>}</div>
        <div className="panel tabla-panel tabla-scroll"><h2>Por categoría</h2><table><thead><tr><th>Categoría</th><th>Unidades</th><th>Total bruto</th></tr></thead><tbody>{periodo.categorias.map(c => <tr key={c.producto__categoria_id}><td>{c.producto__categoria__nombre}</td><td>{c.unidades}</td><td>{moneda(c.total)}</td></tr>)}</tbody></table></div></div>
        <p className="detalle">Los productos y categorías muestran ventas brutas y nombres actuales. Los reembolsos se cuentan en el día en que se realizaron.</p>
      </>}
    </section>
    <section className="seccion-reporte"><h2>Conciliación diaria</h2>
      <form className="filtros-periodo" onSubmit={e => { e.preventDefault(); ejecutar(async () => setConciliacion(await reportesApi.conciliacion({ fecha, efectivo_real:efectivo, qr_real:qr }))); }}>
        <label>Fecha<input type="date" value={fecha} disabled={!admin} onChange={e => setFecha(e.target.value)} required /></label>
        <label>Efectivo real (Bs)<input type="number" min="0" step="0.01" value={efectivo} onChange={e => setEfectivo(e.target.value)} required /></label>
        <label>Yape real (Bs)<input type="number" min="0" step="0.01" value={qr} onChange={e => setQr(e.target.value)} required /></label>
        <button className="btn" disabled={ocupado}>Conciliar día</button><button type="button" className="btn-secundario" disabled={ocupado || efectivo === "" || qr === ""} onClick={() => ejecutar(() => generar("CONCILIACION"))}>Descargar conciliación PDF</button>
      </form>
      {conciliacion && <><Totales datos={conciliacion} /><PorMetodo datos={conciliacion} />
        <div className="panel tabla-panel tabla-scroll"><table><thead><tr><th>Método</th><th>Neto esperado</th><th>Real</th><th>Diferencia</th></tr></thead><tbody>{["efectivo","qr"].map(m => <tr key={m}><td>{m === "qr" ? "Yape" : "Efectivo"}</td><td>{moneda(conciliacion.ventas_netas[m])}</td><td>{moneda(conciliacion.recaudado_real[m])}</td><td>{moneda(conciliacion.diferencias[m])}</td></tr>)}</tbody></table><p className={conciliacion.cuadra ? "aviso" : "error"} role="status">{conciliacion.cuadra ? "La caja cuadra." : "Hay diferencias por revisar."} Diferencia total: {moneda(conciliacion.total_diferencia)}</p></div>
      </>}
    </section>
    <section className="seccion-reporte"><h2>Historial de reportes PDF</h2><p className="detalle">Filtra por fecha de emisión. Cada PDF conserva los datos del momento en que fue generado.</p>
      <form className="filtros-periodo" onSubmit={e => {e.preventDefault(); ejecutar(cargarHistorial);}}>
        <label>Emitidos desde<input type="date" value={histDesde} disabled={!admin} onChange={e => setHistDesde(e.target.value)} required /></label><label>Emitidos hasta<input type="date" value={histHasta} disabled={!admin} onChange={e => setHistHasta(e.target.value)} required /></label>
        <button className="btn-secundario" disabled={ocupado}>Consultar historial</button>{admin && <button type="button" className="btn" disabled={ocupado} onClick={() => ejecutar(() => generar("HISTORIAL"))}>Reporte de reportes PDF</button>}
      </form>
      <div className="panel tabla-panel tabla-scroll"><table><thead><tr><th>Reporte</th><th>Período</th><th>Emitido por</th><th>Fecha de emisión</th><th>Archivo</th></tr></thead><tbody>{historial.map(r => <tr key={r.id}><td>#{r.id} · {r.tipo}</td><td>{r.desde} — {r.hasta}</td><td>{r.generado_por}</td><td>{fechaHora(r.generado_en)}</td><td><button className="btn-texto" disabled={ocupado} onClick={() => ejecutar(() => reportesApi.descargar(r.id))}>Descargar PDF #{r.id}</button></td></tr>)}</tbody></table>{!historial.length && <p className="vacio">No hay reportes emitidos en estas fechas.</p>}</div>
    </section>
  </section>;
}
