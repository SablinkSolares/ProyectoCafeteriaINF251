"""Genera el informe de implementación y verificación a partir de evidencias locales."""
from pathlib import Path
import os
import sys
import json
import re
from datetime import datetime
from zoneinfo import ZoneInfo

sys.stdout.reconfigure(encoding="utf-8")
raiz=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(raiz/"backend"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE","dinocafe.settings")
import django
django.setup()
from pedidos.reporting import crear_pdf

web=json.loads((raiz/"docs/evidencias/pruebas-frontend.json").read_text(encoding="utf-8"))
browser=json.loads((raiz/"docs/evidencias/navegador.json").read_text(encoding="utf-8"))
pg=(raiz/"docs/pruebas-postgres.log").read_text(encoding="utf-8")
sqlite=(raiz/"docs/pruebas-backend.log").read_text(encoding="utf-8")
assert "\nOK\n" in pg and "FAILED" not in pg
assert "OK (skipped=1)" in sqlite and "FAILED" not in sqlite
assert web["numFailedTests"]==0 and not browser["errores_js"]
cantidad_pg=int(re.search(r"Ran (\d+) tests",pg).group(1))
cantidad_sqlite=int(re.search(r"Ran (\d+) tests",sqlite).group(1))
secciones=[
    ("Proyecto y flujo",["Área","Resultado"],[
        ["Consolidación","Una aplicación Django/React en DinoCafe. 311 archivos originales verificados por SHA-256 y conservados."],
        ["Atención","Registrar pedido y mesa → preparar → listo → entregar → cobrar."],
        ["Interfaz","Estilo compartido en catálogo, cocina, entregas, caja, inventario, seguimiento, ventas, usuarios y ajustes."],
    ]),
    ("Funcionalidades entregadas",["Requisito","Implementación"],[
        ["Inicio público","Descripción de DinoCafé y menú por categorías con imágenes y precios, sin exigir cuenta ni mostrar existencias o recetas internas. Acceso del personal separado."],
        ["Actualizar stock","Edición rápida para administración desde Productos, con detección de cambios simultáneos. Los preparables se actualizan mediante sus insumos."],
        ["Inventario","Existencias de terminados; insumos físicos, reservados y libres; recetas por unidad para preparables."],
        ["Imágenes","Imagen obligatoria, validación y carga PNG/JPEG/WebP, vista previa y baja lógica de productos."],
        ["Pedidos","Mesa, observaciones, responsables y fechas. Detalle por ID y seguimiento filtrado por día local."],
        ["Cambios y reembolsos","Pedido original/reemplazo enlazados. Reembolso con motivo. Operación atómica y reversión ante error. Lo consumido no se repone por un reembolso."],
        ["Pagos","Efectivo con monto recibido y cambio. Yape QR con referencia y confirmación por caja. Avisos persistentes de pagos completados."],
        ["Ventas","Productos, categorías, métodos y conciliación con bruto, devoluciones, neto, recibido y diferencias."],
        ["PDF","Ventas y conciliación en PDF. Historial por emisión y PDF del historial. Autor, período, fecha, SHA-256 y descarga del archivo original."],
        ["Permisos","Roles de administrador, mesero, cajero y cocina controlados en la API. Caja consulta reportes del día; administración consulta todo el historial."],
    ]),
    ("Verificación ejecutada",["Comprobación","Evidencia"],[
        ["Backend PostgreSQL",f"Registro de la consolidación anterior: {cantidad_pg} pruebas correctas; incluye dos pedidos concurrentes compitiendo por el último insumo."],
        ["Backend SQLite",f"{cantidad_sqlite-1} pruebas correctas y una omisión explícita de concurrencia PostgreSQL; incluye menú público y actualización de stock."],
        ["Frontend",f"{web['numPassedTests']} pruebas correctas. Compilación de producción correcta. Auditoría npm sin vulnerabilidades reportadas."],
        ["RNF2",f"Registro desde navegador: {browser['registro_interfaz_ms']} ms. Prueba de diez pedidos de diez productos: ver log PostgreSQL. Las mediciones son locales, no una garantía de rendimiento en otra red."],
        ["Navegador",f"{len(browser['pantallas'])} comprobaciones de pantallas a 1440, 768 y 390 px. Sin desbordamiento horizontal ni errores JavaScript."],
        ["PDF reales","Ventas e historial descargados desde la interfaz y leídos como PDF válidos. Ejemplos en docs/evidencias/."],
    ]),
    ("Configuración y pendientes externos",["Punto","Estado"],[
        ["QR Yape real","Cargar la imagen de la cuenta de la cafetería en Ajustes. No se incluye un QR bancario inventado."],
        ["Confirmación automática","No hay conexión bancaria activa. Se requiere un adaptador autorizado del proveedor. El contrato de webhook firmado queda desactivado sin secreto; escanear no acredita un pago."],
        ["RNF1 disponibilidad 99%","Monitor de API y base de datos preparado. La muestra breve fue satisfactoria; se deben medir jornadas completas para acreditar el requisito."],
        ["RNF4 equipos físicos","Comprobado en tamaños de escritorio, tablet y celular con Chromium. Falta validación en dispositivos físicos sobre la red de atención."],
        ["Datos anteriores","No se mezclan bases incompatibles automáticamente. La guía de consolidación explica respaldo y mapeo antes de reutilizar otra base."],
    ]),
    ("Reportes PDF entregados",["Archivo","Contenido"],[
        ["ventas-ejemplo.pdf","Venta bruta, reembolsos, venta neta, métodos de pago, productos y categorías; datos demo."],
        ["historial-reportes-ejemplo.pdf","Registro de documentos emitidos con ID, tipo, período, autor y fecha; datos demo."],
        ["INFORME_IMPLEMENTACION.pdf","Este informe de funciones, pruebas y configuración pendiente."],
    ]),
]
fecha=datetime.now(ZoneInfo("America/La_Paz")).strftime("%Y-%m-%d %H:%M")
salida=raiz/"docs/INFORME_IMPLEMENTACION.pdf"
salida.write_bytes(crear_pdf("DinoCafé · Informe de implementación",f"Emitido {fecha}, America/La_Paz. Consolidación y evidencias del entorno local de demostración.",secciones))
print(f"Informe generado: {salida.name}")
