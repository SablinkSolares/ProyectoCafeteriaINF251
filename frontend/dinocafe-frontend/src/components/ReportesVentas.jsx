import { useState } from "react";
import { getRol, reportesApi } from "../api";

function fechaLocal() {
  const hoy = new Date();
  hoy.setMinutes(hoy.getMinutes() - hoy.getTimezoneOffset());
  return hoy.toISOString().slice(0, 10);
}

function moneda(valor) {
  return new Intl.NumberFormat("es-BO", { style: "currency", currency: "BOB" }).format(Number(valor));
}

export default function ReportesVentas() {
  const [fecha, setFecha] = useState(fechaLocal);
  const [efectivo, setEfectivo] = useState("");
  const [qr, setQr] = useState("");
  const [reporte, setReporte] = useState(null);
  const [cargando, setCargando] = useState(false);
  const [error, setError] = useState("");
  const [desde, setDesde] = useState(fechaLocal);
  const [hasta, setHasta] = useState(fechaLocal);
  const [periodo, setPeriodo] = useState(null);
  const [cargandoPeriodo, setCargandoPeriodo] = useState(false);
  const [errorPeriodo, setErrorPeriodo] = useState("");

  async function consultarPeriodo(event) {
    event.preventDefault();
    setErrorPeriodo("");
    setPeriodo(null);
    if (desde > hasta) {
      setErrorPeriodo("La fecha inicial debe ser anterior o igual a la fecha final.");
      return;
    }
    setCargandoPeriodo(true);
    try {
      setPeriodo(await reportesApi.ventas(desde, hasta));
    } catch (e) {
      setErrorPeriodo(e.message);
    } finally {
      setCargandoPeriodo(false);
    }
  }

  async function consultar(event) {
    event.preventDefault();
    setCargando(true);
    setError("");
    setReporte(null);
    try {
      setReporte(await reportesApi.conciliacion({ fecha, efectivo_real: efectivo, qr_real: qr }));
    } catch (e) {
      setError(e.message);
    } finally {
      setCargando(false);
    }
  }

  return (
    <section>
      <header className="encabezado"><div>
        <p className="sobretitulo">Administración y caja</p>
        <h1>Ventas y conciliación</h1>
        <p className="detalle">Consulta las ventas y compara los pagos registrados con los montos reales.</p>
      </div></header>
      {getRol() === "administrador" && <section aria-labelledby="titulo-periodo">
        <h2 id="titulo-periodo">Ventas por período</h2>
        <form className="filtros-periodo" onSubmit={consultarPeriodo}>
          <label>Desde<input type="date" value={desde} onChange={(e) => setDesde(e.target.value)} required /></label>
          <label>Hasta<input type="date" value={hasta} onChange={(e) => setHasta(e.target.value)} required /></label>
          <button className="btn-secundario" disabled={cargandoPeriodo}>{cargandoPeriodo ? "Consultando…" : "Consultar período"}</button>
        </form>
        {errorPeriodo && <p className="error" role="alert">{errorPeriodo}</p>}
        {periodo && <>
          <p className="detalle">Del {periodo.desde} al {periodo.hasta} · {periodo.cantidad_pagos} pagos confirmados</p>
          <div className="resumen-ventas">
            <article className="indicador"><span>Ventas brutas</span><strong>{moneda(periodo.total_ventas)}</strong></article>
            <article className="indicador"><span>Reembolsos</span><strong>{moneda(periodo.total_reembolsos)}</strong></article>
            <article className="indicador indicador-destacado"><span>Ventas netas</span><strong>{moneda(periodo.total_neto)}</strong></article>
          </div>
          <p className="detalle">Los desgloses muestran ventas brutas. Los reembolsos se cuentan en la fecha en que se realizaron; las categorías corresponden al catálogo actual.</p>
          <div className="reportes-grid">
            <section className="panel reporte-panel"><h2>Por categoría</h2>
              {periodo.categorias.length ? <ul className="reporte-lista">{periodo.categorias.map((item) => <li key={item.producto__categoria_id}><span>{item.producto__categoria__nombre}<small>{item.unidades} unidades</small></span><strong>{moneda(item.total)}</strong></li>)}</ul> : <p className="detalle">No hay ventas en este período.</p>}
            </section>
          </div>
          <section className="panel tabla-panel"><div className="tabla-cabecera"><h2>Ventas por producto</h2></div>
            {periodo.productos.length ? <div className="tabla-scroll"><table><thead><tr><th>Producto</th><th>Categoría</th><th>Unidades</th><th>Venta bruta</th></tr></thead>
              <tbody>{periodo.productos.map((item) => <tr key={item.producto_id}><td>{item.producto__nombre}</td><td>{item.producto__categoria__nombre}</td><td>{item.unidades}</td><td>{moneda(item.total)}</td></tr>)}</tbody></table></div> : <p className="detalle">No hay productos vendidos en este período.</p>}
          </section>
        </>}
      </section>}
      <h2>Conciliación diaria</h2>
      <form className="filtros-periodo" onSubmit={consultar}>
        <label>Fecha<input type="date" value={fecha} onChange={(e) => setFecha(e.target.value)} required /></label>
        <label>Efectivo real (Bs)<input type="number" min="0" step="0.01" value={efectivo} onChange={(e) => setEfectivo(e.target.value)} required /></label>
        <label>QR real (Bs)<input type="number" min="0" step="0.01" value={qr} onChange={(e) => setQr(e.target.value)} required /></label>
        <button className="btn" disabled={cargando}>{cargando ? "Consultando…" : "Conciliar día"}</button>
      </form>
      {error && <p className="error" role="alert">{error}</p>}
      {reporte && <>
        <div className="resumen-ventas">
          <article className="indicador"><span>Ventas brutas</span><strong>{moneda(reporte.total_ventas)}</strong></article>
          <article className="indicador"><span>Reembolsos</span><strong>{moneda(reporte.total_reembolsos)}</strong></article>
          <article className="indicador indicador-destacado"><span>Ventas netas</span><strong>{moneda(reporte.total_neto)}</strong></article>
          <article className="indicador"><span>Diferencia total</span><strong>{moneda(reporte.total_diferencia)}</strong></article>
        </div>
        <div className="reportes-grid">
          <section className="panel reporte-panel"><h2>Por método de pago</h2>
            <ul className="reporte-lista">{["efectivo", "qr"].map((metodo) => <li key={metodo}>
              <span>{metodo === "qr" ? "QR" : "Efectivo"} · diferencia {moneda(reporte.diferencias[metodo])}</span>
              <strong>{moneda(reporte.ventas_netas[metodo])}</strong>
            </li>)}</ul>
            <p role="status">{reporte.cuadra ? "La caja cuadra." : "Hay diferencias por revisar."}</p>
          </section>
        </div>
      </>}
    </section>
  );
}
