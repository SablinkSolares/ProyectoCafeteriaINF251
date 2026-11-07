import { useEffect, useState } from "react";
import { configuracionApi, inventarioApi } from "../api";

export default function ConfiguracionPagos() {
  const [config, setConfig] = useState(null);
  const [error, setError] = useState("");
  const [aviso, setAviso] = useState("");
  const [ocupado, setOcupado] = useState(false);
  useEffect(() => { configuracionApi.obtener().then(setConfig).catch(e => setError(e.message)); }, []);
  async function guardar(e) { e.preventDefault(); setOcupado(true); setError(""); try { setConfig(await configuracionApi.guardar(config)); setAviso("Configuración guardada."); } catch(err) { setError(err.message); } finally { setOcupado(false); } }
  async function subir(e) { const f = e.target.files[0]; if(!f) return; setOcupado(true); try { const data = await inventarioApi.subirImagen(f); setConfig(c => ({...c, imagen_qr:data.imagen})); } catch(err) { setError(err.message); } finally { setOcupado(false); } }
  return <section><header className="encabezado"><div><p className="sobretitulo">Administración</p><h1>Configuración de pagos</h1></div></header>
    {config && <form className="panel form" onSubmit={guardar}>
      <h2>Yape · Bolivia</h2><label className="checkbox-label"><input type="checkbox" checked={config.qr_habilitado} onChange={e => setConfig(c => ({...c,qr_habilitado:e.target.checked}))} />Habilitar pagos Yape por QR</label>
      <label>Subir imagen del QR<input type="file" accept="image/png,image/jpeg,image/webp" onChange={subir} /></label>
      <label>Ruta o URL del QR<input value={config.imagen_qr} onChange={e => setConfig(c => ({...c,imagen_qr:e.target.value}))} /></label>
      {config.imagen_qr && <div className="qr-empresa"><img src={config.imagen_qr} alt="QR de la cafetería" /><button type="button" className="btn-texto" onClick={() => setConfig(c => ({...c, imagen_qr:""}))}>Quitar imagen QR</button></div>}
      <p className="detalle">Carga el QR de tu cuenta Yape. Caja verifica el ingreso y confirma el pago después de entregar el pedido.</p>
      <button className="btn" disabled={ocupado}>{ocupado ? "Guardando…" : "Guardar configuración"}</button>
    </form>}{error && <p className="error" role="alert">{error}</p>}{aviso && <p className="aviso" role="status">{aviso}</p>}
  </section>;
}
