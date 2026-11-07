import { useEffect, useState } from "react";

// RF9: barra de búsqueda con filtrado dinámico. Espera a que la persona deje de
// escribir antes de pedir resultados al endpoint (?q=, coincidencia ILIKE en Django).
export default function BuscadorProductos({ onBuscar, retraso = 300, disabled = false }) {
  const [texto, setTexto] = useState("");

  useEffect(() => {
    const espera = setTimeout(() => onBuscar(texto.trim()), retraso);
    return () => clearTimeout(espera);
  }, [texto, retraso, onBuscar]);

  function limpiar() {
    setTexto("");
    onBuscar("");
  }

  return (
    <div className="buscador" role="search">
      <input
        type="search"
        disabled={disabled}
        value={texto}
        onChange={(e) => setTexto(e.target.value)}
        onKeyDown={(e) => { if (e.key === "Escape") limpiar(); }}
        placeholder="Buscar producto, por ejemplo: café"
        aria-label="Buscar producto"
        autoComplete="off"
      />
      {texto && (
        <button type="button" className="btn-texto" onClick={limpiar} aria-label="Limpiar búsqueda">
          Limpiar
        </button>
      )}
    </div>
  );
}
