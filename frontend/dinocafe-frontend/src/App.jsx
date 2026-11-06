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

const ROLES = new Set(["administrador", "mesero", "cajero", "cocina"]);
const VISTAS = [
  { id: "catalogo", nombre: "Productos", roles: ["administrador", "mesero", "cajero", "cocina"], componente: Catalogo },
  { id: "seguimiento", nombre: "Seguimiento", roles: ["administrador"], componente: SeguimientoPedidos },
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
      setActual(INICIO_POR_ROL[usuario.rol] ?? null);
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
    setActual(INICIO_POR_ROL[datos.rol] ?? null);
  }

  function salir() {
    cerrarSesion();
    setSesion({ estado: "anonima", rol: null, usuario: null, error: "" });
    setActual(null);
  }

  if (sesion.estado === "verificando") {
    return <main className="login-cargando"><p className="detalle" role="status">Validando sesión…</p></main>;
  }
  if (sesion.estado !== "autenticada") {
    return <Login onIngresar={entrar} errorInicial={sesion.error} />;
  }

  const permitidas = VISTAS.filter((vista) => vista.roles.includes(sesion.rol));
  const seleccionada = permitidas.find((vista) => vista.id === actual) ?? permitidas[0];

  return (
    <>
      <nav className="barra" aria-label="Navegación principal">
        <a className="marca" href="#inicio" onClick={(event) => { event.preventDefault(); setActual(permitidas[0]?.id); }}>
          <span className="marca-icono">D</span><span>DinoCafé</span>
        </a>
        <div className="navegacion">
          {permitidas.map((vista) => (
            <button key={vista.id} className={`pestana ${seleccionada.id === vista.id ? "activa" : ""}`}
              aria-current={seleccionada.id === vista.id ? "page" : undefined} onClick={() => setActual(vista.id)}>
              {vista.nombre}
            </button>
          ))}
        </div>
        <div className="cuenta-activa"><span className="cuenta-nombre">{sesion.usuario}</span><span className="cuenta-rol">{NOMBRES_ROL[sesion.rol]}</span></div>
        <button className="btn-texto salir" onClick={salir}>Salir</button>
      </nav>
      <main className="contenedor"><VistaProtegida key={seleccionada.id} vista={seleccionada} rol={sesion.rol} /></main>
    </>
  );
}
