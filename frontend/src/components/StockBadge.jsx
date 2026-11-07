// RF4: indicador visual de disponibilidad. Reutilizable en catálogo, mesero y cocina.
export const STOCK_BAJO = 5;

export function nivelStock(stock) {
  if (stock <= 0) return "agotado";
  if (stock <= STOCK_BAJO) return "bajo";
  return "ok";
}

export default function StockBadge({ stock }) {
  if (stock == null) return null;
  const nivel = nivelStock(stock);
  const texto =
    nivel === "agotado" ? "Agotado" : nivel === "bajo" ? `Quedan ${stock}` : `Disponible: ${stock}`;
  const descripcion =
    nivel === "agotado"
      ? "Producto sin existencias"
      : nivel === "bajo"
        ? `Stock bajo: quedan ${stock} unidades`
        : `Stock disponible: ${stock} unidades`;
  return <span className={`badge badge-${nivel}`} title={descripcion}>{texto}</span>;
}
