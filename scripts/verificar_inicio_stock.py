"""Comprueba portada pública y edición de stock; restaura el stock al finalizar."""
import json
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

sys.stdout.reconfigure(encoding="utf-8")
raiz = Path(__file__).resolve().parents[1]
evidencias = raiz / "docs" / "evidencias"
base = "http://localhost:5173"
resultado = {"pantallas": [], "errores_js": []}

with sync_playwright() as p:
    browser = p.chromium.launch()
    contexto = browser.new_context(viewport={"width": 1440, "height": 1000})
    page = contexto.new_page()
    page.on("pageerror", lambda e: resultado["errores_js"].append(str(e)))
    page.goto(base)
    expect(page.get_by_role("heading", name="Nuestro menú", exact=True)).to_be_visible()
    expect(page.locator(".menu-producto").first).to_be_visible()
    assert not page.get_by_label("Usuario", exact=True).count()
    assert not page.get_by_role("button", name="Guardar stock").count()
    assert not page.locator(".badge").count()
    menu = contexto.request.get(base + "/api/menu/")
    assert menu.status == 200
    assert all("stock" not in producto and "insumos" not in producto for producto in menu.json()["productos"])
    for ancho, alto, nombre in [(1440, 1000, "escritorio"), (768, 1024, "tablet"), (390, 844, "celular")]:
        page.set_viewport_size({"width": ancho, "height": alto})
        assert page.evaluate("document.documentElement.scrollWidth") <= ancho + 2
        page.screenshot(path=str(evidencias / f"inicio-{nombre}.png"), full_page=True)
        resultado["pantallas"].append(nombre)
    page.set_viewport_size({"width": 1440, "height": 1000})
    page.get_by_role("button", name="Acceso del personal", exact=True).click()
    page.get_by_label("Usuario", exact=True).fill("admin")
    page.get_by_label("Contraseña", exact=True).fill("admin123")
    page.get_by_role("button", name="Ingresar", exact=True).click()
    expect(page.get_by_role("heading", name="Catálogo", exact=True)).to_be_visible()
    card = page.locator(".lista-productos > li").filter(has=page.get_by_role("heading", name="Pan", exact=True))
    card.get_by_role("button", name="Actualizar stock de Pan", exact=True).click()
    campo = page.get_by_label("Nuevo stock disponible", exact=True)
    anterior = int(campo.input_value())
    campo.fill(str(anterior + 1))
    modificado = False
    try:
        with page.expect_response(lambda r: r.request.method == "PATCH" and r.url.endswith("/stock/")) as guardado:
            page.get_by_role("button", name="Guardar stock", exact=True).click()
        assert guardado.value.status == 200, guardado.value.text()
        stock_url = guardado.value.url
        modificado = True
        expect(page.get_by_text("Stock de Pan actualizado.", exact=True)).to_be_visible()
        expect(card.locator(".badge")).to_contain_text(str(anterior + 1))
        page.screenshot(path=str(evidencias / "stock-administrador.png"), full_page=True)
        resultado["actualizacion_stock"] = "Guardado desde el catálogo y visualización comprobados"
    finally:
        if modificado:
            token = page.evaluate("localStorage.getItem('access_token')")
            restaurado = contexto.request.patch(stock_url, headers={"Authorization": f"Bearer {token}"}, data={"stock": anterior, "stock_anterior": anterior + 1})
            assert restaurado.status == 200, "No se sobrescribió un cambio concurrente; revisar el stock de prueba."
            resultado["stock_restaurado"] = True
    page.get_by_role("button", name="Ver menú", exact=True).click()
    expect(page.get_by_role("heading", name="Nuestro menú", exact=True)).to_be_visible()
    page.get_by_role("link", name="Ver menú", exact=True).click()
    expect(page.get_by_role("heading", name="Nuestro menú", exact=True)).to_be_visible()
    page.get_by_role("button", name="Volver al panel", exact=True).click()
    page.get_by_role("button", name="Salir", exact=True).click()
    expect(page.get_by_role("heading", name="Nuestro menú", exact=True)).to_be_visible()
    assert not resultado["errores_js"], resultado["errores_js"]
    browser.close()

(evidencias / "inicio-stock.json").write_text(json.dumps(resultado, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(resultado, ensure_ascii=False, indent=2))
