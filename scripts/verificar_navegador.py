"""Prueba funcional en el entorno DEMO local. Crea una venta y reportes de prueba.

Instalar: .venv/Scripts/python -m pip install -r requirements-dev.txt
          .venv/Scripts/python -m playwright install chromium
Ejecutar con backend y frontend activos: .venv/Scripts/python scripts/verificar_navegador.py
"""
from pathlib import Path
import json
import time
import sys
from datetime import datetime
from zoneinfo import ZoneInfo
from playwright.sync_api import sync_playwright, expect
from pypdf import PdfReader
sys.stdout.reconfigure(encoding="utf-8")

raiz=Path(__file__).resolve().parents[1]
evidencias=raiz/"docs"/"evidencias"
evidencias.mkdir(parents=True,exist_ok=True)
base="http://localhost:5173"
resultado={"escenarios":[],"pantallas":[],"errores_js":[]}

with sync_playwright() as p:
    navegador=p.chromium.launch()
    contexto=navegador.new_context(viewport={"width":1440,"height":1000},accept_downloads=True)
    pagina=contexto.new_page()
    pagina.on("pageerror",lambda e:resultado["errores_js"].append(str(e)))
    def entrar(usuario):
        pagina.goto(base + "/#login")
        if pagina.evaluate("Boolean(localStorage.getItem('access_token'))"):
            expect(pagina.get_by_role("button",name="Salir",exact=True)).to_be_visible()
            pagina.get_by_role("button",name="Salir",exact=True).click()
            pagina.get_by_role("button",name="Acceso del personal",exact=True).click()
        pagina.get_by_label("Usuario",exact=True).fill(usuario)
        pagina.get_by_label("Contraseña",exact=True).fill(usuario+"123")
        pagina.get_by_role("button",name="Ingresar",exact=True).click()
        expect(pagina.get_by_role("navigation")).to_be_visible()

    entrar("admin")
    expect(pagina.get_by_role("heading",name="Catálogo",exact=True)).to_be_visible()
    expect(pagina.locator(".lista-productos li").first).to_be_visible()
    pagina.screenshot(path=str(evidencias/"catalogo-escritorio.png"),full_page=True)
    resultado["escenarios"].append("Catálogo muestra imágenes, stock exacto y tipos de producto")
    pagina.get_by_role("button",name="Inventario",exact=True).click()
    expect(pagina.get_by_role("heading",name="Insumos e inventario",exact=True)).to_be_visible()
    expect(pagina.get_by_role("columnheader",name="Disponible",exact=True)).to_be_visible()
    resultado["escenarios"].append("Inventario muestra físico, reservado y disponible")

    entrar("mesero")
    producto=pagina.locator(".producto-caja").filter(has=pagina.get_by_role("heading",name="Pan",exact=True))
    producto.get_by_role("button",name="Agregar",exact=True).click()
    pagina.get_by_label("Mesa",exact=True).select_option("7")
    pagina.get_by_label("Observaciones",exact=True).fill("Verificación local del flujo completo")
    inicio=time.perf_counter()
    with pagina.expect_response(lambda r:r.request.method=="POST" and r.url.endswith("/api/pedidos/")) as respuesta:
        pagina.get_by_role("button",name="Registrar pedido",exact=True).click()
    datos=respuesta.value.json()
    assert respuesta.value.status==201,datos
    pedido=datos["id"]
    dia_pedido=datetime.fromisoformat(datos["creado_en"].replace("Z","+00:00")).astimezone(ZoneInfo("America/La_Paz")).date().isoformat()
    resultado["registro_interfaz_ms"]=round((time.perf_counter()-inicio)*1000,2)
    assert resultado["registro_interfaz_ms"]<5000
    resultado["pedido_de_prueba"]=pedido
    resultado["escenarios"].append("Mesero registra pedido con mesa y observaciones")

    entrar("cocina")
    pagina.get_by_role("button",name=f"Empezar a preparar del pedido {pedido}",exact=True).click()
    pagina.get_by_role("button",name=f"Marcar como listo del pedido {pedido}",exact=True).click()
    resultado["escenarios"].append("Cocina prepara sin exigir pago previo")
    entrar("mesero")
    tarjeta=pagina.locator(".pedido-operacion").filter(has=pagina.get_by_role("heading",name=f"#{pedido}",exact=True))
    tarjeta.get_by_role("button",name="Confirmar entrega",exact=True).click()
    resultado["escenarios"].append("Mesero confirma entrega")

    entrar("cajero")
    tarjeta=pagina.locator(".pedido-operacion").filter(has=pagina.get_by_role("link",name=f"Pedido #{pedido}",exact=True))
    tarjeta.get_by_label("Método de pago").select_option("QR")
    tarjeta.get_by_label("Referencia del comprobante").fill(f"PRUEBA-LOCAL-YAPE-{pedido}")
    tarjeta.get_by_role("button",name="Registrar comprobante QR",exact=True).click()
    pagina.get_by_role("button",name="Verificar QR",exact=True).click()
    tarjeta.get_by_role("button",name="Confirmar pago Yape recibido",exact=True).click()
    pagina.get_by_role("button",name="Pagados",exact=True).click()
    expect(tarjeta.get_by_text("Pago realizado",exact=True)).to_be_visible()
    pagina.get_by_role("button",name="Avisos",exact=False).click()
    expect(pagina.locator(".avisos-panel").get_by_text(f"Pago realizado: pedido #{pedido}",exact=False)).to_be_visible(timeout=10000)
    resultado["escenarios"].append("Yape pendiente → confirmación de caja → notificación de pago realizado")

    entrar("admin")
    pagina.get_by_role("button",name="Seguimiento",exact=True).click()
    expect(pagina.get_by_label("Día de seguimiento")).to_be_visible()
    pagina.get_by_label("Día de seguimiento").fill(dia_pedido)
    pagina.get_by_role("link",name=f"Pedido #{pedido}",exact=True).click()
    expect(pagina.get_by_role("heading",name=f"Pedido #{pedido}",exact=True)).to_be_visible()
    expect(pagina.get_by_text("Verificación local del flujo completo",exact=True)).to_be_visible()
    resultado["escenarios"].append("Seguimiento diario y detalle por ID muestran trazabilidad")
    pagina.get_by_role("button",name="Ventas",exact=True).click()
    pagina.get_by_role("button",name="Consultar período",exact=True).click()
    expect(pagina.get_by_text("Yape · QR",exact=True)).to_be_visible()
    for boton,nombre in [("Descargar ventas PDF","ventas-ejemplo.pdf"),("Reporte de reportes PDF","historial-reportes-ejemplo.pdf")]:
        with pagina.expect_download() as descarga:
            pagina.get_by_role("button",name=boton,exact=True).click()
        ruta=evidencias/nombre
        descarga.value.save_as(ruta)
        lector=PdfReader(ruta)
        texto="\n".join(hoja.extract_text() for hoja in lector.pages)
        assert "DinoCafé" in texto
        resultado["escenarios"].append(f"{nombre}: PDF válido de {len(lector.pages)} página(s)")
    expect(pagina.get_by_role("button",name="Descargar PDF",exact=False).first).to_be_visible()

    for ancho,alto,tipo in [(1440,1000,"escritorio"),(768,1024,"tablet"),(390,844,"celular")]:
        pagina.set_viewport_size({"width":ancho,"height":alto})
        for seccion,titulo in [("Productos","Catálogo"),("Caja","Caja"),("Inventario","Insumos e inventario"),("Seguimiento","Seguimiento de pedidos"),("Ventas","Ventas y reportes"),("Usuarios","Gestión de usuarios"),("Ajustes","Configuración de pagos"),("Cocina","Cocina")]:
            pagina.get_by_role("button",name=seccion,exact=True).click()
            # El encabezado confirma que el cambio de vista ya terminó.
            expect(pagina.locator("main h1")).to_be_visible()
            pagina.wait_for_timeout(150)
            ancho_documento=pagina.evaluate("document.documentElement.scrollWidth")
            assert ancho_documento<=ancho+2,(tipo,seccion,ancho_documento)
            resultado["pantallas"].append({"tipo":tipo,"vista":seccion,"ancho":ancho,"ancho_documento":ancho_documento})
            if seccion in {"Caja","Ventas","Inventario"}:
                pagina.screenshot(path=str(evidencias/f"{seccion.lower()}-{tipo}.png"),full_page=True)
    assert not resultado["errores_js"],resultado["errores_js"]
    navegador.close()

(evidencias/"navegador.json").write_text(json.dumps(resultado,ensure_ascii=False,indent=2),encoding="utf-8")
print(json.dumps(resultado,ensure_ascii=False,indent=2))
