"""Consultas contables y documentos inmutables de los reportes emitidos."""
import hashlib
from decimal import Decimal
from io import BytesIO
from xml.sax.saxutils import escape
from django.core.serializers.json import DjangoJSONEncoder
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.db.models import Sum, Count, F, DecimalField, ExpressionWrapper
from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from .models import Pago, Reembolso, DetallePedido, ReportePDF
import json


def fecha_valida(valor):
    try:
        fecha = parse_date(str(valor))
    except (TypeError, ValueError):
        fecha = None
    if not fecha:
        raise ValidationError({"fecha": "Usa una fecha válida AAAA-MM-DD."})
    return fecha


def periodo(request, datos=None):
    datos = datos if datos is not None else request.query_params
    hoy = timezone.localdate()
    desde = fecha_valida(datos.get("desde", hoy.isoformat()))
    hasta = fecha_valida(datos.get("hasta", hoy.isoformat()))
    if desde > hasta:
        raise ValidationError({"periodo": "Desde debe ser anterior o igual a Hasta."})
    if request.user.rol not in {"administrador", "cajero"}:
        raise PermissionDenied("Solo administración y caja consultan reportes.")
    if request.user.rol == "cajero" and (desde != hoy or hasta != hoy):
        raise PermissionDenied("Caja solo consulta y concilia el día actual.")
    return desde, hasta


def dinero(valor):
    return format(valor or Decimal("0"), ".2f")


def ventas(desde, hasta):
    pagos = Pago.objects.filter(estado__in=["COMPLETADO", "REEMBOLSADO"], pagado_en__date__range=(desde, hasta))
    devoluciones = Reembolso.objects.filter(fecha_hora_reembolso__date__range=(desde, hasta))
    bruto = pagos.aggregate(total=Sum("monto"))["total"] or Decimal("0")
    devuelto = devoluciones.aggregate(total=Sum("importe_reembolsado"))["total"] or Decimal("0")
    metodos = {}
    for metodo, clave in [("EFECTIVO", "efectivo"), ("QR", "qr")]:
        venta = pagos.filter(metodo=metodo).aggregate(total=Sum("monto"), cantidad=Count("id"))
        devolucion = devoluciones.filter(pago__metodo=metodo).aggregate(total=Sum("importe_reembolsado"), cantidad=Count("id"))
        metodos[clave] = {"cantidad": venta["cantidad"], "ventas": dinero(venta["total"]), "cantidad_reembolsos": devolucion["cantidad"], "reembolsos": dinero(devolucion["total"]), "neto": dinero((venta["total"] or Decimal("0")) - (devolucion["total"] or Decimal("0")))}
    lineas = DetallePedido.objects.filter(pedido__pago__in=pagos)
    subtotal = ExpressionWrapper(F("cantidad") * F("precio_unitario"), output_field=DecimalField(max_digits=20, decimal_places=2))
    productos = list(lineas.values("producto_id", "producto__nombre", "producto__categoria__nombre").annotate(unidades=Sum("cantidad"), total=Sum(subtotal)).order_by("producto__nombre"))
    categorias = list(lineas.values("producto__categoria_id", "producto__categoria__nombre").annotate(unidades=Sum("cantidad"), total=Sum(subtotal)).order_by("producto__categoria__nombre"))
    return {"desde": desde.isoformat(), "hasta": hasta.isoformat(), "cantidad_pagos": pagos.count(), "total_ventas": dinero(bruto), "total_reembolsos": dinero(devuelto), "total_neto": dinero(bruto-devuelto), "por_metodo": metodos, "productos": productos, "categorias": categorias}


def conciliar(request):
    datos = request.data
    fecha = fecha_valida(datos.get("fecha", ""))
    periodo(request, {"desde": fecha, "hasta": fecha})
    campo = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0"))
    reales = {m: campo.run_validation(datos.get(f"{m}_real")) for m in ["efectivo", "qr"]}
    resumen = ventas(fecha, fecha)
    metodos = resumen["por_metodo"]
    diferencias = {m: reales[m] - Decimal(metodos[m]["neto"]) for m in reales}
    return {**resumen, "fecha": fecha.isoformat(), "ventas": {m: {"cantidad": d["cantidad"], "total": d["ventas"]} for m,d in metodos.items()}, "reembolsos": {m: {"cantidad": d["cantidad_reembolsos"], "total": d["reembolsos"]} for m,d in metodos.items()}, "ventas_netas": {m: d["neto"] for m,d in metodos.items()}, "recaudado_real": {m: dinero(v) for m,v in reales.items()}, "diferencias": {m: dinero(v) for m,v in diferencias.items()}, "total_real": dinero(sum(reales.values())), "total_diferencia": dinero(sum(diferencias.values())), "cuadra": all(v == 0 for v in diferencias.values())}


def crear_pdf(titulo, subtitulo, secciones):
    salida = BytesIO()
    estilos = getSampleStyleSheet()
    doc = SimpleDocTemplate(salida, pagesize=A4, rightMargin=36, leftMargin=36, topMargin=42, bottomMargin=42, title=titulo, author="DinoCafé")
    story = [Paragraph(escape(titulo), estilos["Title"]), Paragraph(escape(subtitulo), estilos["Normal"]), Spacer(1, 18)]
    for nombre, cabecera, filas in secciones:
        story.extend([Paragraph(escape(nombre), estilos["Heading2"]), Spacer(1, 6)])
        datos = [[Paragraph(escape(str(c)), estilos["Normal"]) for c in fila] for fila in [cabecera] + (filas or [["Sin registros"] + [""] * (len(cabecera)-1)])]
        tabla = Table(datos, colWidths=[doc.width/len(cabecera)] * len(cabecera), repeatRows=1, hAlign="LEFT")
        tabla.setStyle(TableStyle([("BACKGROUND", (0,0),(-1,0), colors.HexColor("#e9efea")), ("VALIGN", (0,0),(-1,-1), "TOP"), ("LINEBELOW", (0,0),(-1,-1), .3, colors.HexColor("#d5ddd5")), ("TOPPADDING", (0,0),(-1,-1), 7), ("BOTTOMPADDING", (0,0),(-1,-1), 7)]))
        story.extend([tabla, Spacer(1, 16)])
    def pie(canvas, documento):
        canvas.setFont("Helvetica", 8)
        canvas.drawString(36, 22, "DinoCafe | Importes en bolivianos (Bs) | America/La_Paz")
        canvas.drawRightString(A4[0]-36, 22, f"Pagina {documento.page}")
    doc.build(story, onFirstPage=pie, onLaterPages=pie)
    return salida.getvalue()


def metadata(reporte):
    return {"id": reporte.pk, "tipo": reporte.tipo, "desde": reporte.desde, "hasta": reporte.hasta, "generado_por": reporte.generado_por.username if reporte.generado_por else "Usuario eliminado", "generado_en": reporte.generado_en, "sha256": reporte.sha256, "resumen": reporte.resumen, "url": f"/api/reportes/{reporte.pk}/pdf/"}


class ReportesView(APIView):
    def get(self, request):
        desde, hasta = periodo(request)
        qs = ReportePDF.objects.select_related("generado_por").defer("contenido").filter(generado_en__date__range=(desde, hasta))
        if request.user.rol == "cajero":
            qs = qs.filter(generado_por=request.user)
        return Response([metadata(r) for r in qs])

    def post(self, request):
        tipo = request.data.get("tipo", "VENTAS")
        datos = request.data
        if tipo == "CONCILIACION":
            resumen = conciliar(request)
            desde = hasta = fecha_valida(resumen["fecha"])
        else:
            desde, hasta = periodo(request, datos)
            resumen = ventas(desde, hasta) if tipo == "VENTAS" else {}
        secciones = []
        if tipo in {"VENTAS", "CONCILIACION"}:
            secciones.append(("Resumen de ventas", ["Ventas brutas", "Reembolsos", "Ventas netas", "Pagos"], [[resumen["total_ventas"], resumen["total_reembolsos"], resumen["total_neto"], resumen["cantidad_pagos"]]]))
            secciones.append(("Por método de pago", ["Método", "Ventas", "Reembolsos", "Neto"], [[m, d["ventas"], d["reembolsos"], d["neto"]] for m,d in resumen["por_metodo"].items()]))
            secciones.append(("Productos (ventas brutas)", ["Producto", "Categoría", "Unidades", "Total"], [[p["producto__nombre"], p["producto__categoria__nombre"], p["unidades"], p["total"]] for p in resumen["productos"]]))
            secciones.append(("Categorías (ventas brutas)", ["Categoría", "Unidades", "Total"], [[p["producto__categoria__nombre"], p["unidades"], p["total"]] for p in resumen["categorias"]]))
            if tipo == "CONCILIACION":
                secciones.append(("Conciliación de caja", ["Método", "Neto esperado", "Real recibido", "Diferencia"], [[m, resumen["ventas_netas"][m], resumen["recaudado_real"][m], resumen["diferencias"][m]] for m in ["efectivo", "qr"]]))
        elif tipo == "HISTORIAL":
            if request.user.rol != "administrador":
                raise PermissionDenied("Solo administración genera el reporte de reportes PDF.")
            registros = list(ReportePDF.objects.select_related("generado_por").defer("contenido").filter(generado_en__date__range=(desde, hasta)))
            resumen = {"cantidad_reportes": len(registros), "ids": [r.pk for r in registros]}
            secciones = [("Reportes PDF emitidos", ["ID / Tipo", "Período", "Generado por / fecha"], [[f"{r.pk} / {r.tipo}", f"{r.desde} - {r.hasta}", f"{r.generado_por.username if r.generado_por else '-'} / {timezone.localtime(r.generado_en):%Y-%m-%d %H:%M}"] for r in registros])]
        else:
            raise ValidationError({"tipo": "Usa VENTAS, CONCILIACION o HISTORIAL."})
        contenido = crear_pdf(f"DinoCafé · {tipo.title()}", f"Del {desde} al {hasta}. Emitido por {request.user.username}. Los reembolsos se contabilizan en su fecha; productos y categorías muestran ventas brutas y nombres actuales.", secciones)
        reporte = ReportePDF.objects.create(tipo=tipo, desde=desde, hasta=hasta, generado_por=request.user, resumen=json.loads(json.dumps(resumen, cls=DjangoJSONEncoder)), contenido=contenido, sha256=hashlib.sha256(contenido).hexdigest())
        return Response(metadata(reporte), status=201)


class DescargarReporteView(APIView):
    def get(self, request, pk):
        if request.user.rol not in {"administrador", "cajero"}:
            raise PermissionDenied("No tienes permiso para descargar reportes.")
        reporte = get_object_or_404(ReportePDF, pk=pk)
        if request.user.rol == "cajero" and (reporte.generado_por_id != request.user.pk or reporte.desde != timezone.localdate() or reporte.hasta != timezone.localdate()):
            raise PermissionDenied("Caja solo descarga sus reportes del día actual.")
        response = HttpResponse(bytes(reporte.contenido), content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="dinocafe-{reporte.tipo.lower()}-{reporte.pk}.pdf"'
        return response
