import { useCallback, useEffect, useMemo, useState } from "react";
import { pedidosApi, productosApi, configuracionApi } from "../api";
import StockBadge from "./StockBadge";
import ImagenProducto from "./ImagenProducto";

function moneda(valor) {
  return new Intl.NumberFormat("es-BO", { style: "currency", currency: "BOB" }).format(Number(valor));
}

export function NuevoPedidoCaja({ alCrear, refreshToken, puedeCrear = false, pedidoOriginal = null, alCancelar }) {
  const [mesa, setMesa] = useState(pedidoOriginal?.mesa ?? 1);
  const [observaciones, setObservaciones] = useState("");
  const [motivo, setMotivo] = useState("");
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
        productosApi.listar({ activo: "true" }),
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
      const datos = {
        mesa: Number(mesa), observaciones, motivo,
        detalles: carrito.map((linea) => ({ producto: linea.id, cantidad: linea.cantidad })),
      };
      const pedido = pedidoOriginal ? await pedidosApi.cambiar(pedidoOriginal.id, datos) : await pedidosApi.crear(datos);
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
          <h2>{pedidoOriginal ? `Cambiar pedido #${pedidoOriginal.id}` : "Registrar nuevo pedido"}</h2>
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
          <label>Mesa<select aria-label="Mesa" value={mesa} onChange={e => setMesa(e.target.value)}>{Array.from({length:10}, (_,i) => <option key={i+1} value={i+1}>Mesa {i+1}</option>)}</select></label>
          <label>Observaciones<input value={observaciones} onChange={e => setObservaciones(e.target.value)} maxLength={500} /></label>
          {pedidoOriginal && <label>Motivo del cambio<input value={motivo} onChange={e => setMotivo(e.target.value)} maxLength={500} required /></label>}
          <div className="carrito-total"><span>Total del pedido</span><strong>{moneda(total)}</strong></div>
          <button className="btn" disabled={!puedeCrear || guardando || carrito.length === 0 || (pedidoOriginal && !motivo.trim())} onClick={registrarPedido}>
            {guardando ? "Registrando…" : pedidoOriginal ? "Confirmar cambio" : "Registrar pedido"}
          </button>
          {!puedeCrear && <p className="detalle">El registro corresponde a caja o administración.</p>}
        {alCancelar && <button className="btn-texto" onClick={alCancelar}>Cerrar cambio</button>}
        </aside>
      </div>
      {error && <p className="error" role="alert">{error}</p>}
      {aviso && <p className="aviso" role="status">{aviso}</p>}
    </section>
  );
}

function PedidoCaja({ pedido, alActualizar, config, alCambiar }) {
  const [metodo, setMetodo] = useState("EFECTIVO");
  const [monto, setMonto] = useState(pedido.total);
  const [referencia, setReferencia] = useState("");
  const [motivo, setMotivo] = useState("");
  const [ocupado, setOcupado] = useState(false);
  const [error, setError] = useState("");
  const [aviso, setAviso] = useState("");
  const pago = pedido.pago;
  async function ejecutar(accion, mensaje) {
    setOcupado(true); setError(""); setAviso("");
    try { await accion(); setAviso(mensaje); await alActualizar(); }
    catch(e) { setError(e.message); }
    finally { setOcupado(false); }
  }
  function cobrar(e) {
    e.preventDefault();
    ejecutar(() => pedidosApi.registrarPago(pedido.id, {
      metodo, monto: pedido.total, monto_recibido: metodo === "QR" ? pedido.total : monto,
      referencia_qr: metodo === "QR" ? referencia : "",
    }), metodo === "QR" ? "Comprobante Yape registrado. Pendiente de confirmación." : "Pago realizado.");
  }
  return <article className="pedido-operacion">
    <header className="pedido-operacion-cabecera">
      <div><p className="sobretitulo">Mesa {pedido.mesa} · {pedido.estado.replaceAll("_"," ")}</p><h2><a href={`#pedido/${pedido.id}`}>Pedido #{pedido.id}</a></h2><p className="detalle">Registrado por {pedido.registrado_por_nombre || "—"}</p></div>
      <strong>{moneda(pedido.total)}</strong>
    </header>
    <ul className="lineas-pedido">{pedido.detalles.map(d => <li key={d.id}><span>{d.cantidad}× {d.producto}</span><strong>{moneda(d.subtotal)}</strong></li>)}</ul>
    {pedido.observaciones && <p className="nota-pedido">{pedido.observaciones}</p>}
    {pedido.pedido_original && <p className="detalle">Reemplaza al pedido <a href={`#pedido/${pedido.pedido_original}`}>#{pedido.pedido_original}</a>: {pedido.motivo_cambio}</p>}
    {!pago && pedido.estado !== "ENTREGADO" && pedido.estado !== "CANCELADO" && <p className="detalle">El cobro se habilita después de confirmar la entrega.</p>}
    {!pago && pedido.estado === "ENTREGADO" && <form className="form-cobro" onSubmit={cobrar}>
      <label>Método de pago<select value={metodo} onChange={e => setMetodo(e.target.value)}>
        <option value="EFECTIVO">Efectivo</option>{config?.qr_habilitado && <option value="QR">Yape · QR</option>}
      </select></label>
      {metodo === "EFECTIVO" ? <>
        <label>Monto recibido (Bs)<input type="number" min={pedido.total} step="0.01" value={monto} onChange={e => setMonto(e.target.value)} required /></label>
        <p className="detalle">Cambio: <b>{moneda(Math.max(0,Number(monto)-Number(pedido.total)))}</b></p>
      </> : <>
        {config?.imagen_qr ? <div className="qr-empresa"><img src={config.imagen_qr} alt="Código QR de pago de la cafetería" /></div> : <p className="detalle">Solicita el QR de la cafetería en caja.</p>}
        <p className="detalle">Después de pagar, registra la referencia del comprobante. Caja verificará la recepción del dinero.</p>
        <label>Referencia del comprobante<input value={referencia} maxLength={255} onChange={e => setReferencia(e.target.value)} required /></label>
      </>}
      <button className="btn" disabled={ocupado}>{ocupado ? "Guardando…" : metodo === "QR" ? "Registrar comprobante QR" : "Registrar pago"}</button>
    </form>}
    {pago && <div className="resumen-pago">
      <p><b>{pago.metodo === "QR" ? "Yape · QR" : "Efectivo"}</b> · <span className={pago.estado === "COMPLETADO" ? "badge badge-ok" : "badge"}>{pago.estado === "COMPLETADO" ? "Pago realizado" : pago.estado}</span></p>
      {pago.referencia_qr && <p className="detalle">Referencia: {pago.referencia_qr}</p>}
      {pago.metodo === "EFECTIVO" && <p className="detalle">Recibido: {moneda(pago.monto_recibido)} · Cambio: {moneda(pago.cambio)}</p>}
      {pago.estado === "PENDIENTE" && <button className="btn" disabled={ocupado} onClick={() => ejecutar(() => pedidosApi.verificarQr(pago.id), "Pago realizado por Yape.")}>Confirmar pago Yape recibido</button>}
      {pago.estado === "COMPLETADO" && <form className="form-cobro" onSubmit={e => { e.preventDefault(); ejecutar(() => pedidosApi.registrarReembolso(pago.id,{motivo}), "Reembolso registrado."); }}>
        <p className="detalle">Reembolso total: {moneda(pago.monto)}. Los pedidos activos se cancelarán; lo ya preparado no vuelve al inventario.</p>
        <label>Motivo del reembolso<input value={motivo} onChange={e => setMotivo(e.target.value)} maxLength={500} required /></label>
        <button className="btn-secundario" disabled={ocupado}>Registrar reembolso</button>
      </form>}
      {pago.estado === "REEMBOLSADO" && <p className="detalle">Motivo: {pago.motivo_reembolso}</p>}
    </div>}
    {(pedido.estado !== "CANCELADO" && (pedido.estado !== "ENTREGADO" || pago?.estado === "COMPLETADO")) && <div className="acciones">
      <button className="btn-secundario" disabled={ocupado} onClick={() => alCambiar(pedido)}>Cambiar pedido</button>
      {pedido.estado !== "ENTREGADO" && (!pago || pago.estado === "PENDIENTE") && <button className="btn-texto" disabled={ocupado} onClick={() => { const motivo = window.prompt("Motivo de cancelación"); if(motivo?.trim()) ejecutar(() => pedidosApi.cancelar(pedido.id,motivo),"Pedido cancelado."); }}>Cancelar pedido</button>}
    </div>}
    {pedido.estado === "CANCELADO" && <p className="detalle">Cancelación: {pedido.motivo_cancelacion}</p>}
    {error && <p className="error" role="alert">{error}</p>}
    {aviso && <p className="aviso" role="status">{aviso}</p>}
  </article>;
}

export default function VistaCaja() {
  const [pedidos, setPedidos] = useState([]);
  const [config, setConfig] = useState(null);
  const [error, setError] = useState("");
  const [filtro, setFiltro] = useState("pendientes");
  const [cambio, setCambio] = useState(null);
  const [version, setVersion] = useState(0);
  const cargar = useCallback(async () => {
    try { const [lista, ajustes] = await Promise.all([pedidosApi.listarCaja(), configuracionApi.obtener()]); setPedidos(lista); setConfig(ajustes); setError(""); }
    catch(e) { setError(e.message); }
  }, []);
  useEffect(() => { cargar(); const timer = setInterval(cargar,5000); return () => clearInterval(timer); }, [cargar]);
  const visibles = pedidos.filter(p => filtro === "todos" || (filtro === "pendientes" ? p.estado === "ENTREGADO" && !p.pago : filtro === "verificar" ? p.pago?.estado === "PENDIENTE" : ["COMPLETADO","REEMBOLSADO"].includes(p.pago?.estado)));
  async function creado() { setVersion(v => v+1); setFiltro("pendientes"); await cargar(); }
  return <section>
    <header className="encabezado"><div><p className="sobretitulo">Atención y cobros</p><h1>Caja</h1><p className="detalle">Registra pedidos y cobra después de que el mesero confirme la entrega.</p></div><button className="btn-secundario" onClick={cargar}>Actualizar</button></header>
    {cambio ? <div className="panel cambio-panel"><p className="aviso">El cambio cancela el original y registra su reembolso si fue pagado. El nuevo pedido requiere un nuevo cobro.</p><NuevoPedidoCaja key={cambio.id} pedidoOriginal={cambio} puedeCrear alCancelar={() => setCambio(null)} alCrear={async () => { setCambio(null); await creado(); }} /></div> :
      <NuevoPedidoCaja puedeCrear alCrear={creado} refreshToken={version} />}
    <section className="caja-pedidos"><h2>Pedidos registrados</h2>
      <div className="chips">{[["pendientes","Por cobrar"],["verificar","Verificar QR"],["pagados","Pagados"],["todos","Todos"]].map(([id,nombre]) => <button key={id} className={`chip ${filtro === id ? "activo" : ""}`} onClick={() => setFiltro(id)}>{nombre}</button>)}</div>
      {error && <p className="error" role="alert">{error}</p>}
      {!visibles.length && <p className="vacio">No hay pedidos en esta sección.</p>}
      <div className="lista-operaciones">{visibles.map(p => <PedidoCaja key={p.id} pedido={p} config={config} alActualizar={cargar} alCambiar={setCambio} />)}</div>
    </section>
  </section>;
}
