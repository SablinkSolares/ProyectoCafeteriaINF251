import { useState } from "react";
import { reportesApi } from "../api";

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
        <p className="detalle">Compara los pagos registrados con los montos reales de un día.</p>
      </div></header>
      <div className="filtros-periodo" aria-label="Consulta por periodo">
        <label>Desde<input type="date" disabled /></label>
        <label>Hasta<input type="date" disabled /></label>
        <button type="button" className="btn-secundario" disabled>Consultar periodo</button>
      </div>
      <p className="detalle">El reporte por rango de fechas y producto aún no está disponible.</p>
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
          <section className="panel reporte-panel"><h2>Por categoría</h2><p className="detalle">El desglose por categoría aún no está disponible.</p></section>
        </div>
      </>}
      <section className="panel tabla-panel"><div className="tabla-cabecera"><h2>Ventas por producto y periodo</h2></div>
        <p className="detalle">El servidor actual ofrece conciliación diaria; el detalle por producto y rango de fechas aún no está disponible.</p>
        <div className="tabla-scroll"><table><thead><tr><th>Producto</th><th>Categoría</th><th>Unidades</th><th>Total</th></tr></thead></table></div>
      </section>
    </section>
  );
}
