import { useEffect, useState } from "react";
import {
  authApi,
  cerrarSesion,
  getToken,
  guardarSesion,
} from "./api";
import Catalogo from "./components/Catalogo";
import GestionUsuarios from "./components/GestionUsuarios";
import Login from "./components/Login";
import ReportesVentas from "./components/ReportesVentas";
import SeguimientoPedidos from "./components/SeguimientoPedidos";
import VistaCaja from "./components/VistaCaja";
import VistaCocina from "./components/VistaCocina";
import VistaMesero from "./components/VistaMesero";
import Inventario from "./components/Inventario";
import ConfiguracionPagos from "./components/ConfiguracionPagos";
import Notificaciones from "./components/Notificaciones";
import DetallePedido from "./components/DetallePedido";
import Inicio from "./components/Inicio";

const ROLES = new Set(["administrador", "mesero", "cajero", "cocina"]);
const VISTAS = [
  { id: "catalogo", nombre: "Productos", roles: ["administrador", "mesero", "cajero", "cocina"], componente: Catalogo },
  { id: "seguimiento", nombre: "Seguimiento", roles: ["administrador", "cajero"], componente: SeguimientoPedidos },
  { id: "inventario", nombre: "Inventario", roles: ["administrador"], componente: Inventario },
  { id: "ajustes", nombre: "Ajustes", roles: ["administrador"], componente: ConfiguracionPagos },
  { id: "pedidos", nombre: "Entregas", roles: ["administrador", "mesero"], componente: VistaMesero },
  { id: "caja", nombre: "Caja", roles: ["administrador", "cajero"], componente: VistaCaja },
  { id: "ventas", nombre: "Ventas", roles: ["administrador", "cajero"], componente: ReportesVentas },
  { id: "usuarios", nombre: "Usuarios", roles: ["administrador"], componente: GestionUsuarios },
  { id: "cocina", nombre: "Cocina", roles: ["administrador", "cocina"], componente: VistaCocina },
];
const NOMBRES_ROL = {
  administrador: "Administrador",
  mesero: "Mesero",
  cajero: "Caja",
  cocina: "Cocina",
};
const INICIO_POR_ROL = { administrador: "catalogo", mesero: "pedidos", cajero: "caja", cocina: "cocina" };

function VistaProtegida({ vista, rol }) {
  if (!vista || !vista.roles.includes(rol)) {
    return <p className="error" role="alert">No tienes permiso para acceder a esta sección.</p>;
  }
  const Componente = vista.componente;
  return <Componente />;
}

export default function App() {
  const [sesion, setSesion] = useState({
    estado: getToken() ? "verificando" : "anonima",
    rol: null,
    usuario: null,
    error: "",
  });
  const [actual, setActual] = useState(null);
  const [ruta, setRuta] = useState(() => location.hash.slice(1));
  useEffect(() => { const cambiar = () => { const valor=location.hash.slice(1); setRuta(valor); if(!valor.startsWith("pedido/")) setActual(valor); }; window.addEventListener("hashchange",cambiar); return () => window.removeEventListener("hashchange",cambiar); }, []);
  function seleccionar(id) { setActual(id); setRuta(id); location.hash=id; }

  useEffect(() => {
    if (!getToken()) return undefined;
    let activa = true;
    authApi.me().then((usuario) => {
      if (!activa) return;
      if (!ROLES.has(usuario.rol)) {
        cerrarSesion();
        setSesion({ estado: "anonima", rol: null, usuario: null, error: "La cuenta no tiene un rol válido." });
        return;
      }
      guardarSesion({ access: getToken(), rol: usuario.rol, username: usuario.username });
      setSesion({ estado: "autenticada", rol: usuario.rol, usuario: usuario.username, error: "" });
      setActual(location.hash.slice(1) || INICIO_POR_ROL[usuario.rol] || null);
    }).catch((error) => {
      if (!activa) return;
      if (error.status === 401) cerrarSesion();
      setSesion({
        estado: "anonima", rol: null, usuario: null,
        error: error.status === 401
          ? "Tu sesión venció. Ingresa de nuevo."
          : "No se pudo validar la sesión. Comprueba la conexión e inténtalo otra vez.",
      });
    });
    return () => { activa = false; };
  }, []);

  async function entrar(datos) {
    if (!ROLES.has(datos.rol)) throw new Error("La cuenta no tiene un rol válido.");
    guardarSesion(datos);
    setSesion({ estado: "autenticada", rol: datos.rol, usuario: datos.username, error: "" });
    seleccionar(INICIO_POR_ROL[datos.rol] ?? "catalogo");
  }

  function salir() {
    cerrarSesion();
    setSesion({ estado: "anonima", rol: null, usuario: null, error: "" });
    setActual(null);
    location.hash = "";
    setRuta("");
  }

  if (sesion.estado === "verificando") {
    return <main className="login-cargando"><p className="detalle" role="status">Validando sesión…</p></main>;
  }
  if (["", "inicio", "nuestro-menu"].includes(ruta) || (sesion.estado !== "autenticada" && ruta !== "login")) {
    return <Inicio sesionActiva={sesion.estado === "autenticada"} onAcceder={() => seleccionar(sesion.estado === "autenticada" ? INICIO_POR_ROL[sesion.rol] : "login")} />;
  }
  if (sesion.estado !== "autenticada") {
    return <Login onIngresar={entrar} errorInicial={sesion.error} onVolver={() => seleccionar("inicio")} />;
  }

  const permitidas = VISTAS.filter((vista) => vista.roles.includes(sesion.rol));
  const seleccionada = permitidas.find((vista) => vista.id === actual) ?? permitidas[0];

  return (
    <>
      <nav className="barra" aria-label="Navegación principal">
        <a className="marca" href="#inicio" onClick={(event) => { event.preventDefault(); seleccionar("inicio"); }}>
          <img className="marca-logo" src="/images/dinocafe-logo.svg" alt="" /><span>DinoCafé</span>
        </a>
        <div className="navegacion">
          <button className="pestana" onClick={() => seleccionar("inicio")}>Ver menú</button>
          {permitidas.map((vista) => (
            <button key={vista.id} className={`pestana ${seleccionada.id === vista.id ? "activa" : ""}`}
              aria-current={seleccionada.id === vista.id ? "page" : undefined} onClick={() => seleccionar(vista.id)}>
              {vista.nombre}
            </button>
          ))}
        </div>
        <Notificaciones />
        <div className="cuenta-activa"><span className="cuenta-nombre">{sesion.usuario}</span><span className="cuenta-rol">{NOMBRES_ROL[sesion.rol]}</span></div>
        <button className="btn-texto salir" onClick={salir}>Salir</button>
      </nav>
      <main className="contenedor">{/^pedido\/\d+$/.test(ruta) ? <DetallePedido key={ruta} id={Number(ruta.split("/")[1])} /> : <VistaProtegida key={seleccionada.id} vista={seleccionada} rol={sesion.rol} />}</main>
    </>
  );
}
