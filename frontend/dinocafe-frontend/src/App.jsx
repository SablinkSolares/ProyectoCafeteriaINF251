import { useState } from "react";
import { cerrarSesion, getRol, getToken } from "./api";
import Catalogo from "./components/Catalogo";
import LoginDev from "./components/LoginDev";
import VistaCocina from "./components/VistaCocina";

// Navegación mínima por rol. La pantalla de login y las rutas protegidas completas
// son de S1-T02 (Noemi); aquí solo se oculta lo que el rol no usa. El servidor decide (RNF3).
const VISTAS = [
  { id: "catalogo", nombre: "Catálogo", roles: ["administrador", "mesero", "cajero", "cocina"], componente: Catalogo },
  { id: "cocina", nombre: "Cocina", roles: ["administrador", "cocina"], componente: VistaCocina },
];

export default function App() {
  const [token, setToken] = useState(getToken());
  const [rol, setRol] = useState(getRol());
  const permitidas = VISTAS.filter((v) => v.roles.includes(rol));
  const [actual, setActual] = useState(() => VISTAS.find((v) => v.roles.includes(getRol()))?.id);

  function entrar(nuevoRol) {
    setToken(getToken());
    setRol(nuevoRol);
    setActual(VISTAS.find((v) => v.roles.includes(nuevoRol))?.id);
  }

  function salir() {
    cerrarSesion();
    setToken(null);
    setRol(null);
    setActual(undefined);
  }

  if (!token || !rol || permitidas.length === 0) {
    return <LoginDev onIngresar={entrar} />;
  }

  const Vista = permitidas.find((v) => v.id === actual)?.componente ?? permitidas[0].componente;

  return (
    <>
      <nav className="barra">
        <span className="marca">DinoCafé</span>
        {permitidas.map((v) => (
          <button key={v.id} className={`pestana ${actual === v.id ? "activa" : ""}`} onClick={() => setActual(v.id)}>
            {v.nombre}
          </button>
        ))}
        <button className="btn-texto salir" onClick={salir}>Salir</button>
      </nav>
      <main className="contenedor"><Vista /></main>
    </>
  );
}
