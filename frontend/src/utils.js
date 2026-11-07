export const moneda = valor => new Intl.NumberFormat("es-BO", { style: "currency", currency: "BOB" }).format(Number(valor || 0));
export const fechaLocal = () => new Intl.DateTimeFormat("en-CA", { timeZone: "America/La_Paz", year: "numeric", month: "2-digit", day: "2-digit" }).format(new Date());
export const fechaHora = valor => valor ? new Date(valor).toLocaleString("es-BO", { timeZone: "America/La_Paz", dateStyle: "short", timeStyle: "short" }) : "Pendiente";
export const ESTADOS = { ESPERA: "En espera", EN_PREPARACION: "En preparación", LISTO: "Listo para entregar", ENTREGADO: "Entregado", CANCELADO: "Cancelado" };
