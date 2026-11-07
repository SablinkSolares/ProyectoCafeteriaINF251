import { useEffect, useState } from "react";
import { notificacionesApi, getUsuario } from "../api";

export default function Notificaciones() {
  const [lista, setLista] = useState([]);
  const [abierto, setAbierto] = useState(false);
  const [error, setError] = useState("");
  const clave = `notificaciones-vistas:${getUsuario()}`;
  const [visto, setVisto] = useState(() => Number(localStorage.getItem(clave) || 0));
  useEffect(() => {
    let activa = true, cursor = 0, enCurso = false;
    async function cargar() {
      if(enCurso) return; enCurso = true;
      try {
        const nuevos = await notificacionesApi.listar(cursor);
        if(!activa) return;
        if(nuevos.length) { cursor = Math.max(...nuevos.map(n => n.id)); setLista(actual => [...nuevos.reverse(), ...actual].slice(0,50)); }
        setError("");
      } catch(e) { if(activa) setError("No se pudieron actualizar los avisos."); }
      finally { enCurso = false; }
    }
    cargar(); const timer = setInterval(cargar,4000);
    return () => { activa=false; clearInterval(timer); };
  }, []);
  const pendientes = lista.filter(n => n.id > visto).length;
  function abrir() { setAbierto(!abierto); if(lista.length) { const id = Math.max(...lista.map(n => n.id)); setVisto(id); localStorage.setItem(clave,String(id)); } }
  return <div className="avisos">
    <button className="btn-secundario" onClick={abrir} aria-expanded={abierto}>Avisos {pendientes > 0 && <span className="badge badge-ok">{pendientes}</span>}</button>
    <span className="sr-only" role="status">{pendientes ? `${pendientes} avisos nuevos` : ""}</span>
    {abierto && <div className="avisos-panel"><h2>Notificaciones</h2>{error && <p className="error" role="alert">{error}</p>}{!lista.length && <p className="detalle">Sin notificaciones.</p>}
      <ul>{lista.map(n => <li key={n.id}><a href={`#pedido/${n.pedido_id}`} onClick={() => setAbierto(false)}>{n.mensaje}</a><small>{new Date(n.creado_en).toLocaleTimeString("es-BO")}</small></li>)}</ul>
    </div>}
  </div>;
}
