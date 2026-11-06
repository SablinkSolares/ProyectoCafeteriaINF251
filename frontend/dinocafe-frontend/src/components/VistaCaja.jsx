import { useCallback, useEffect, useMemo, useState } from "react";
import { getRol, pedidosApi, productosApi } from "../api";
import StockBadge from "./StockBadge";
import ImagenProducto from "./ImagenProducto";

function moneda(valor) {
  return new Intl.NumberFormat("es-BO", { style: "currency", currency: "BOB" }).format(Number(valor));
}

export function NuevoPedidoCaja({ alCrear, refreshToken, puedeCrear = false }) {
  const [productos, setProductos] = useState([]);
  const [categorias, setCategorias] = useState([]);
  const [categoria, setCategoria] = useState("");
  const [busqueda, setBusqueda] = useState("");
  const [carrito, setCarrito] = useState([]);
  const [cargando, setCargando] = useState(true);
  const [guardando, setGuardando] = useState(false);
  const [error, setError] = useState("");
  const [aviso, setAviso] = useState("");

  const cargarCatalogo = useCallback(async (silencioso = false) => {
    if (!silencioso) setCargando(true);
    try {
      const [listaProductos, listaCategorias] = await Promise.all([
        productosApi.listar(),
        productosApi.categorias(),
      ]);
      setProductos(listaProductos);
      setCategorias(listaCategorias);
    } catch (e) {
      setError(e.message);
    } finally {
      setCargando(false);
    }
  }, []);

  useEffect(() => { cargarCatalogo(); }, [cargarCatalogo, refreshToken]);
  useEffect(() => {
    const timer = setInterval(() => cargarCatalogo(true), 10000);
    return () => clearInterval(timer);
  }, [cargarCatalogo]);

  const visibles = useMemo(() => productos.filter((producto) => {
    const coincideTexto = producto.nombre.toLowerCase().includes(busqueda.trim().toLowerCase());
    const coincideCategoria = !categoria || String(producto.categoria) === categoria;
    return coincideTexto && coincideCategoria;
  }), [productos, busqueda, categoria]);

  const total = carrito.reduce((suma, linea) => suma + Number(linea.precio) * linea.cantidad, 0);

  function agregar(producto) {
    setError("");
    setAviso("");
    const existente = carrito.find((linea) => linea.id === producto.id);
    if (existente) {
      if (existente.cantidad >= producto.stock) {
        setError(`No hay suficiente stock de ${producto.nombre}.`);
        return;
      }
      setCarrito(carrito.map((linea) => linea.id === producto.id ? { ...linea, cantidad: linea.cantidad + 1 } : linea));
      return;
    }
    if (producto.stock < 1) {
      setError(`${producto.nombre} está agotado.`);
      return;
    }
    setCarrito([...carrito, { id: producto.id, nombre: producto.nombre, precio: producto.precio, stock: producto.stock, cantidad: 1 }]);
  }

  function cambiarCantidad(id, cantidad) {
    const producto = carrito.find((linea) => linea.id === id);
    if (!producto) return;
    if (cantidad < 1) {
      setCarrito((actual) => actual.filter((linea) => linea.id !== id));
      return;
    }
    if (cantidad > producto.stock) {
      setError(`Stock máximo de ${producto.nombre}: ${producto.stock}.`);
      return;
    }
    setCarrito((actual) => actual.map((linea) => linea.id === id ? { ...linea, cantidad } : linea));
    setError("");
  }

  async function registrarPedido(event) {
    event.preventDefault();
    if (carrito.length === 0) {
      setError("Agrega al menos un producto al pedido.");
      return;
    }
    setGuardando(true);
    setError("");
    setAviso("");
    try {
      const pedido = await pedidosApi.crear({
        detalles: carrito.map((linea) => ({ producto: linea.id, cantidad: linea.cantidad })),
      });
      setCarrito([]);
      setAviso(`Pedido #${pedido.id} registrado correctamente.`);
      await alCrear();
      await cargarCatalogo(true);
    } catch (e) {
      await cargarCatalogo();
      setError(e.message);
    } finally {
      setGuardando(false);
    }
  }

  return (
    <section className="panel caja-nuevo-pedido">
      <div className="tabla-cabecera">
        <div>
          <p className="sobretitulo">Registro de pedidos</p>
          <h2>Registrar nuevo pedido</h2>
          <p className="detalle">Al registrar el pedido se comprueban y reservan productos e insumos disponibles.</p>
        </div>
      </div>

      <div className="caja-constructor">
        <div>
          <div className="buscador caja-buscador">
            <input aria-label="Buscar producto para el pedido" placeholder="Buscar producto…" value={busqueda}
              onChange={(event) => setBusqueda(event.target.value)} />
          </div>
          <div className="chips" role="group" aria-label="Categorías de productos para el pedido">
            <button className={`chip ${categoria === "" ? "activo" : ""}`} onClick={() => setCategoria("")}>Todos</button>
            {categorias.map((item) => (
              <button key={item.id} className={`chip ${categoria === String(item.id) ? "activo" : ""}`}
                onClick={() => setCategoria(String(item.id))}>{item.nombre}</button>
            ))}
          </div>
          {cargando && <p className="vacio">Cargando catálogo…</p>}
          <div className="productos-caja">
            {visibles.map((producto) => (
              <article className="producto producto-caja" key={producto.id}>
                <ImagenProducto src={producto.imagen} nombre={producto.nombre} />
                <div className="producto-informacion">
                  <h3>{producto.nombre}</h3>
                  <p className="detalle">{producto.categoria_nombre}</p>
                  <strong className="precio">{moneda(producto.precio)}</strong>
                </div>
                <div className="producto-derecha">
                  <StockBadge stock={producto.stock} />
                  <button className="btn-secundario" disabled={producto.stock < 1 || cargando}
                    onClick={() => agregar(producto)}>{producto.stock < 1 ? "Agotado" : "Agregar"}</button>
                </div>
              </article>
            ))}
            {!cargando && visibles.length === 0 && <p className="vacio">No se encontraron productos.</p>}
          </div>
        </div>

        <aside className="carrito-caja">
          <div className="pedido-operacion-cabecera">
            <div><p className="sobretitulo">Pedido</p><h2>Carrito</h2></div>
            <span className="contador">{carrito.reduce((suma, linea) => suma + linea.cantidad, 0)} artículos</span>
          </div>
          {carrito.length === 0 ? <p className="vacio">Selecciona productos para comenzar el pedido.</p> : (
            <ul className="carrito-lista">
              {carrito.map((linea) => (
                <li key={linea.id}>
                  <div><b>{linea.nombre}</b><small>{moneda(linea.precio)} c/u</small></div>
                  <div className="cantidad-control">
                    <button type="button" className="btn-texto" aria-label={`Quitar una unidad de ${linea.nombre}`}
                      onClick={() => cambiarCantidad(linea.id, linea.cantidad - 1)}>−</button>
                    <strong>{linea.cantidad}</strong>
                    <button type="button" className="btn-texto" aria-label={`Agregar una unidad de ${linea.nombre}`}
                      disabled={linea.cantidad >= linea.stock}
                      onClick={() => cambiarCantidad(linea.id, linea.cantidad + 1)}>+</button>
                  </div>
                </li>
              ))}
            </ul>
          )}
          <div className="carrito-total"><span>Total del pedido</span><strong>{moneda(total)}</strong></div>
          <button className="btn" disabled={!puedeCrear || guardando || carrito.length === 0} onClick={registrarPedido}>
            {guardando ? "Registrando…" : "Registrar pedido"}
          </button>
          {!puedeCrear && <p className="detalle">El registro corresponde al mesero o administrador.</p>}
        </aside>
      </div>
      {error && <p className="error" role="alert">{error}</p>}
      {aviso && <p className="aviso" role="status">{aviso}</p>}
    </section>
  );
}

function PedidoCaja({ pedido, alActualizar }) {
  const [metodo, setMetodo] = useState("EFECTIVO");
  const [monto, setMonto] = useState(pedido.total);
  const [referencia, setReferencia] = useState("");
  const [motivo, setMotivo] = useState("");
  const [qrDisponible, setQrDisponible] = useState(true);
  const [ocupado, setOcupado] = useState(false);
  const [error, setError] = useState("");
  const [aviso, setAviso] = useState("");
  const pago = pedido.pago;
  const reembolsado = pago?.estado === "REEMBOLSADO" ? Number(pago.monto) : 0;
  const disponible = Math.max(0, Number(pedido.total) - reembolsado);

  async function ejecutar(accion, mensaje, filtroSiguiente = null) {
    setOcupado(true);
    setError("");
    setAviso("");
    try {
      await accion();
      setAviso(mensaje);
      await alActualizar(filtroSiguiente);
      return true;
    } catch (e) {
      setError(e.message);
      return false;
    } finally {
      setOcupado(false);
    }
  }

  function cobrar(event) {
    event.preventDefault();
    ejecutar(
      () => pedidosApi.registrarPago(pedido.id, {
        metodo,
        monto: pedido.total,
        referencia_qr: metodo === "QR" ? referencia : "",
      }),
      metodo === "QR"
        ? "Referencia registrada. El QR es de demostración; la confirmación se realiza manualmente."
        : "Pago en efectivo registrado.",
      metodo === "QR" ? "verificar" : "pagados",
    );
  }

  async function reembolsar(event) {
    event.preventDefault();
    const guardado = await ejecutar(
      () => pedidosApi.registrarReembolso(pago.id, { motivo }),
      "Reembolso registrado.",
    );
    if (guardado) setMotivo("");
  }

  return (
    <article className="pedido-operacion">
      <header className="pedido-operacion-cabecera">
        <div>
          <p className="sobretitulo">Pedido</p>
          <h2>#{pedido.id}</h2>
          <p className="detalle">Responsable no registrado por el servidor.</p>
        </div>
        <strong className="total-pedido">{moneda(pedido.total)}</strong>
      </header>
      <ul className="lineas-pedido">
        {pedido.detalles.map((detalle) => (
          <li key={detalle.id}><span>{detalle.cantidad}× {detalle.producto}</span><span>{moneda(detalle.subtotal)}</span></li>
        ))}
      </ul>

      {!pago && pedido.estado !== "ENTREGADO" && <p className="detalle">Pendiente de entrega. El cobro se habilitará después de la entrega.</p>}
      {!pago && pedido.estado === "ENTREGADO" && (
        <form className="form-cobro" onSubmit={cobrar}>
          <label>Método de pago
            <select value={metodo} onChange={(event) => setMetodo(event.target.value)}>
              <option value="EFECTIVO">Efectivo</option>
              <option value="QR">QR</option>
            </select>
          </label>
          {metodo === "QR" ? (
            <div className="qr-empresa">
              <p><b>QR de demostración</b></p>
              {qrDisponible ? (
                <img src="/qr-demostracion.svg" alt="Código QR ficticio de demostración"
                  onError={() => setQrDisponible(false)} />
              ) : (
                <div className="qr-placeholder">
                  <span>QR DE DEMOSTRACIÓN</span>
                  <small>No se pudo cargar la imagen de ejemplo.</small>
                </div>
              )}
              <p className="detalle">Imagen ficticia: no realiza cobros. La confirmación del pago se registra manualmente.</p>
            </div>
          ) : (
            <>
              <label>Monto recibido (Bs)
                <input type="number" min={pedido.total} step="0.01" value={monto}
                  aria-describedby={`ayuda-efectivo-${pedido.id}`}
                  onChange={(event) => setMonto(event.target.value)} required />
              </label>
              <small id={`ayuda-efectivo-${pedido.id}`}>El monto recibido y el cambio se muestran aquí, pero no se guardan.</small>
            </>
          )}
          {metodo === "QR" && (
            <label>Referencia o número de comprobante
              <input value={referencia} onChange={(event) => setReferencia(event.target.value)} maxLength="120" required />
            </label>
          )}
          {metodo === "EFECTIVO" && Number(monto) >= Number(pedido.total) && (
            <p className="detalle">Cambio: <strong>{moneda(Number(monto) - Number(pedido.total))}</strong></p>
          )}
          <button className="btn" disabled={ocupado}>{ocupado ? "Guardando…" : metodo === "QR" ? "Registrar comprobante QR" : "Registrar pago"}</button>
        </form>
      )}

      {pago && (
        <div className="resumen-pago">
          <p><b>{pago.metodo === "QR" ? "Pago QR" : "Pago en efectivo"}</b> · {pago.estado}</p>
          {pago.metodo === "QR" && <p className="detalle">Comprobante: {pago.referencia_qr || "Sin referencia"}</p>}
          {pago.metodo === "EFECTIVO" && <p className="detalle">Monto registrado: {moneda(pago.monto)}</p>}
          {pago.estado === "PENDIENTE" && pago.metodo === "QR" && (
            <>
              <p className="detalle">Confirmación manual de demostración; el sistema no consulta a ningún banco. El pedido debe estar entregado.</p>
              <button className="btn-secundario" disabled={ocupado || pedido.estado !== "ENTREGADO"} onClick={() =>
                ejecutar(() => pedidosApi.verificarQr(pago.id), "Pago QR confirmado.", "pagados")
              }>Confirmar pago QR manualmente</button>
            </>
          )}
          {["COMPLETADO", "REEMBOLSADO"].includes(pago.estado) && (
            <>
              <p className="detalle">Estado del pedido: {pedido.estado.replaceAll("_", " ").toLowerCase()}</p>
              <p className="detalle">Reembolsado: {moneda(reembolsado)} · Disponible: {moneda(disponible)}</p>
              {pago.estado === "REEMBOLSADO" && <p className="detalle">Motivo: {pago.motivo_reembolso}</p>}
              {pago.estado === "COMPLETADO" && (
                <form className="form-cobro form-reembolso" onSubmit={reembolsar}>
                  <p className="detalle">El servidor admite un único reembolso por el importe total: {moneda(disponible)}.</p>
                  <label>Motivo
                    <input value={motivo} onChange={(event) => setMotivo(event.target.value)} maxLength="240" required />
                  </label>
                  <button className="btn-secundario" disabled={ocupado}>Registrar reembolso</button>
                </form>
              )}
            </>
          )}
        </div>
      )}
      {error && <p className="error" role="alert">{error}</p>}
      {aviso && <p className="aviso" role="status">{aviso}</p>}
    </article>
  );
}

export default function VistaCaja() {
  const [pedidos, setPedidos] = useState([]);
  const [error, setError] = useState("");
  const [filtro, setFiltro] = useState("pendientes");
  const [versionCatalogo, setVersionCatalogo] = useState(0);

  const cargar = useCallback(async (filtroSiguiente = null) => {
    try {
      setPedidos(await pedidosApi.listarCaja());
      if (filtroSiguiente) setFiltro(filtroSiguiente);
      if (filtroSiguiente === "pagados") setVersionCatalogo((version) => version + 1);
      setError("");
    } catch (e) {
      setError(e.message);
    }
  }, []);

  useEffect(() => {
    cargar();
    const timer = setInterval(cargar, 5000);
    return () => clearInterval(timer);
  }, [cargar]);

  const visibles = pedidos.filter((pedido) => {
    if (filtro === "pendientes") return !pedido.pago && pedido.estado === "ENTREGADO";
    if (filtro === "verificar") return pedido.pago?.estado === "PENDIENTE";
    return ["COMPLETADO", "REEMBOLSADO"].includes(pedido.pago?.estado);
  });

  return (
    <section>
      <header className="encabezado">
        <div>
          <p className="sobretitulo">Operaciones</p>
          <h1>Caja</h1>
          <p className="detalle">Consulta los pedidos y registra pagos y reembolsos.</p>
        </div>
        <button className="btn-secundario" onClick={cargar}>Actualizar</button>
      </header>

      <NuevoPedidoCaja alCrear={cargar} refreshToken={versionCatalogo} puedeCrear={getRol() === "administrador"} />

      <section className="caja-pedidos">
        <div className="tabla-cabecera"><div><h2>Pedidos registrados</h2><p className="detalle">Los pedidos aparecen por cobrar cuando el mesero confirma la entrega.</p></div></div>
        <div className="chips" role="group" aria-label="Filtrar pedidos de caja">
          {[["pendientes", "Por cobrar"], ["verificar", "Verificar QR"], ["pagados", "Pagados / en proceso"]].map(([id, titulo]) => (
            <button key={id} className={`chip ${filtro === id ? "activo" : ""}`} onClick={() => setFiltro(id)}>{titulo}</button>
          ))}
        </div>
        {error && <p className="error" role="alert">{error}</p>}
        {visibles.length === 0 && !error && <p className="vacio">No hay pedidos en esta sección.</p>}
        <div className="lista-operaciones">
          {visibles.map((pedido) => <PedidoCaja key={pedido.id} pedido={pedido} alActualizar={cargar} />)}
        </div>
      </section>
    </section>
  );
}
