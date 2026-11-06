import { useEffect, useMemo, useState } from "react";

const IMAGENES_POR_CATEGORIA = {
  bebidas: "/images/carrusel/bebidas.jpg",
  acompanamientos: "/images/carrusel/acompanamientos.jpg",
};

function claveCategoria(nombre = "") {
  return nombre.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase().trim();
}

export default function CarruselCategorias({ categorias = [] }) {
  const diapositivas = useMemo(() => categorias.map((categoria) => {
    const clave = claveCategoria(categoria.nombre);
    return {
      id: categoria.id,
      nombre: categoria.nombre,
      imagen: categoria.imagen_carrusel || IMAGENES_POR_CATEGORIA[clave] || "",
      descripcion: clave === "bebidas"
        ? "Cafés, tés y bebidas para acompañar tu momento."
        : clave === "acompanamientos"
          ? "Masas, pasteles y opciones para disfrutar."
          : `Descubre los productos de ${categoria.nombre}.`,
    };
  }), [categorias]);

  const [indice, setIndice] = useState(0);
  const [imagenesFallidas, setImagenesFallidas] = useState({});

  useEffect(() => {
    setIndice(0);
    setImagenesFallidas({});
  }, [diapositivas.length]);

  useEffect(() => {
    if (diapositivas.length < 2) return undefined;
    const temporizador = window.setInterval(() => {
      setIndice((actual) => (actual + 1) % diapositivas.length);
    }, 5000);
    return () => window.clearInterval(temporizador);
  }, [diapositivas.length]);

  if (diapositivas.length === 0) return null;

  const actual = diapositivas[indice] || diapositivas[0];
  const avanzar = () => setIndice((actualIndice) => (actualIndice + 1) % diapositivas.length);
  const retroceder = () => setIndice((actualIndice) => (actualIndice - 1 + diapositivas.length) % diapositivas.length);

  return (
    <section className="carrusel-categorias" aria-label="Galería de categorías">
      {actual.imagen && !imagenesFallidas[actual.id] ? (
        <img className="carrusel-fondo" src={actual.imagen} alt={`Productos de ${actual.nombre}`}
          onError={() => setImagenesFallidas((actuales) => ({ ...actuales, [actual.id]: true }))} />
      ) : (
        <div className="carrusel-fondo carrusel-imagen-pendiente" aria-hidden="true">
          <span>Coloca tu imagen de {actual.nombre}</span>
        </div>
      )}
      <div className="carrusel-velo" />
      <div className="carrusel-contenido">
        <span className="carrusel-etiqueta">Descubre DinoCafé</span>
        <h2>{actual.nombre}</h2>
        <p>{actual.descripcion}</p>
        <span className="carrusel-indicador">{indice + 1} / {diapositivas.length}</span>
      </div>
      {diapositivas.length > 1 && (
        <>
          <button type="button" className="carrusel-flecha carrusel-anterior"
            onClick={retroceder} aria-label="Categoría anterior">‹</button>
          <button type="button" className="carrusel-flecha carrusel-siguiente"
            onClick={avanzar} aria-label="Categoría siguiente">›</button>
          <div className="carrusel-puntos" aria-label="Seleccionar categoría">
            {diapositivas.map((diapositiva, posicion) => (
              <button type="button" key={diapositiva.id}
                className={`carrusel-punto ${posicion === indice ? "activo" : ""}`}
                aria-label={`Mostrar ${diapositiva.nombre}`} aria-current={posicion === indice ? "true" : undefined}
                onClick={() => setIndice(posicion)} />
            ))}
          </div>
        </>
      )}
    </section>
  );
}
