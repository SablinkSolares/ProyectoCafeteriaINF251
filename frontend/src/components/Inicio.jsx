import { useEffect, useState } from "react";
import { menuApi } from "../api";
import { moneda } from "../utils";
import ImagenProducto from "./ImagenProducto";

export default function Inicio({ onAcceder, sesionActiva = false }) {
  const [menu, setMenu] = useState({ categorias: [], productos: [] });
  const [categoria, setCategoria] = useState("");
  const [estado, setEstado] = useState("cargando");
  const [error, setError] = useState("");
  const [intento, setIntento] = useState(0);

  useEffect(() => {
    let activo = true;
    setEstado("cargando");
    menuApi.obtener().then(datos => {
      if (!activo) return;
      setMenu(datos);
      setEstado("listo");
    }).catch(err => {
      if (!activo) return;
      setError(err.message);
      setEstado("error");
    });
    return () => { activo = false; };
  }, [intento]);

  const categorias = menu.categorias.filter(c => !categoria || String(c.id) === categoria);

  return <div className="inicio-publico">
    <header className="inicio-barra">
      <a className="marca" href="#inicio"><img className="marca-logo" src="/images/dinocafe-logo.svg" alt="" /><span>DinoCafé</span></a>
      <nav aria-label="Navegación del menú"><a href="#nuestro-menu">Ver menú</a><button type="button" className="btn-texto" onClick={onAcceder}>{sesionActiva ? "Volver al panel" : "Acceso del personal"}</button></nav>
    </header>
    <main>
      <section className="inicio-presentacion" aria-labelledby="inicio-titulo">
        <div className="inicio-texto"><p className="sobretitulo">Bienvenido a DinoCafé</p><h1 id="inicio-titulo">Buen café,<br />buenos momentos.</h1>
          <p>Un espacio para hacer una pausa y disfrutar de un café, una bebida caliente y algo rico para acompañar. Conoce nuestro menú y encuentra tu próximo favorito.</p>
          <a className="btn" href="#nuestro-menu">Descubre nuestro menú <span aria-hidden="true">↓</span></a>
        </div>
        <div className="inicio-foto"><img src="/images/carrusel/bebidas.jpg" alt="Bebidas de DinoCafé" /></div>
      </section>
      <section id="nuestro-menu" className="inicio-menu" aria-labelledby="titulo-menu">
        <header className="inicio-menu-cabecera"><div><p className="sobretitulo">Para disfrutar</p><h2 id="titulo-menu">Nuestro menú</h2></div><p className="detalle">Precios en bolivianos</p></header>
        {estado === "listo" && <div className="chips" role="group" aria-label="Categorías del menú">
          <button className={`chip ${categoria === "" ? "activo" : ""}`} aria-pressed={categoria === ""} onClick={() => setCategoria("")}>Todo el menú</button>
          {menu.categorias.map(c => <button key={c.id} className={`chip ${categoria === String(c.id) ? "activo" : ""}`} aria-pressed={categoria === String(c.id)} onClick={() => setCategoria(String(c.id))}>{c.nombre}</button>)}
        </div>}
        {estado === "cargando" && <p className="vacio" role="status">Preparando el menú…</p>}
        {estado === "error" && <div className="panel inicio-error"><p className="error" role="alert">No pudimos cargar el menú. {error}</p><button className="btn-secundario" onClick={() => setIntento(n => n + 1)}>Volver a intentar</button></div>}
        {estado === "listo" && !menu.productos.length && <p className="vacio">Estamos preparando nuestro menú. Vuelve pronto.</p>}
        {estado === "listo" && categorias.map(c => <section className="menu-categoria" key={c.id} aria-label={c.nombre}>
          <h3>{c.nombre}</h3><ul className="menu-productos">{menu.productos.filter(p => p.categoria === c.id).map(p => <li className="menu-producto" key={p.id}>
            <ImagenProducto src={p.imagen} nombre={p.nombre} /><div><h4>{p.nombre}</h4><p>{p.categoria_nombre}</p></div><strong>{moneda(p.precio)}</strong>
          </li>)}</ul>
        </section>)}
      </section>
    </main>
    <footer className="inicio-pie"><span>DinoCafé</span><p>Una pausa para disfrutar.</p></footer>
  </div>;
}
