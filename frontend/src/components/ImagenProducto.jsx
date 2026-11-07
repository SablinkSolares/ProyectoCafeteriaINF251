import { useEffect, useState } from "react";

// Imagen local desde public/ o URL externa. Si falta el archivo, conserva la tarjeta sin imagen rota.
export default function ImagenProducto({ src, nombre, className = "" }) {
  const [fallo, setFallo] = useState(!src);

  useEffect(() => setFallo(!src), [src]);

  if (!src || fallo) {
    return (
      <div className={`imagen-producto imagen-producto-vacia ${className}`} role="img"
        aria-label={`Imagen pendiente para ${nombre}`}>
        <span>Imagen pendiente</span>
      </div>
    );
  }

  return (
    <img className={`imagen-producto ${className}`} src={src} alt={nombre}
      loading="lazy" onError={() => setFallo(true)} />
  );
}
