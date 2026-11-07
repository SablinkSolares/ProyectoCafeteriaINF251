import hashlib
import hmac
import json
from datetime import timedelta
from decimal import Decimal
from io import BytesIO
import tempfile
from PIL import Image
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.urls import reverse, resolve
from rest_framework.test import APIClient
from catalogo.models import Categoria, Producto, Insumo, ProductoInsumo, ConfiguracionPago
from .models import Pedido, Pago, ReservaInsumo, Notificacion, Reembolso, ReportePDF


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class FlujoUnificadoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.usuarios = {rol: get_user_model().objects.create_user(username=rol, password="prueba123", rol=rol) for rol in ["administrador", "cajero", "mesero", "cocina"]}
        cls.cat = Categoria.objects.create(nombre="Bebidas")
        cls.pan = Producto.objects.create(nombre="Pan", categoria=cls.cat, precio="3.50", stock=10, imagen="/images/productos/pan.jpg")
        cls.cafe = Producto.objects.create(nombre="Café", categoria=cls.cat, precio="7.00", stock=0, preparable=True, imagen="/images/productos/cafe.jpg")
        cls.leche = Insumo.objects.create(nombre_insumo="Leche", unidad_medida="ml", cantidad_stock=1000)
        ProductoInsumo.objects.create(producto=cls.cafe, insumo=cls.leche, cantidad_insumo_por_unidad=200)

    def setUp(self):
        self.client = APIClient()
        self.rol("administrador")

    def rol(self, rol):
        self.client.force_authenticate(self.usuarios[rol])

    def crear(self, producto=None, cantidad=1, **extra):
        res = self.client.post("/api/pedidos/", {"mesa": 3, "detalles": [{"producto": (producto or self.pan).pk, "cantidad": cantidad}], **extra}, format="json")
        self.assertEqual(res.status_code, 201, res.data)
        return res.data

    def avanzar(self, pedido, estado):
        res = self.client.patch(f"/api/pedidos/{pedido['id']}/estado/", {"estado": estado}, format="json")
        self.assertEqual(res.status_code, 200, res.data)
        return res.data

    def entregar(self, pedido):
        self.rol("cocina")
        self.avanzar(pedido, "EN_PREPARACION")
        self.avanzar(pedido, "LISTO")
        self.rol("mesero")
        self.avanzar(pedido, "ENTREGADO")
        self.rol("administrador")

    def pagar(self, pedido, metodo="EFECTIVO", **extra):
        res = self.client.post("/api/pagos/", {"pedido": pedido["id"], "monto": pedido["total"], "metodo": metodo, "referencia_qr": "YAPE-0001" if metodo == "QR" else "", **extra}, format="json")
        self.assertEqual(res.status_code, 201, res.data)
        return res.data

    def test_flujo_entrega_antes_de_cobro_y_responsables(self):
        self.rol("mesero")
        p = self.crear(observaciones="Sin azúcar")
        self.assertEqual(p["estado"], "ESPERA")
        self.rol("cajero")
        intento = self.client.post("/api/pagos/", {"pedido":p["id"],"monto":p["total"],"metodo":"EFECTIVO"}, format="json")
        self.assertEqual(intento.status_code,400)
        self.entregar(p)
        pago = self.pagar(p, monto_recibido="10.00")
        self.assertEqual(pago["cambio"],"6.50")
        actual = self.client.get(f"/api/pedidos/{p['id']}/").data
        self.assertEqual(actual["estado"],"ENTREGADO")
        self.assertEqual(actual["registrado_por_nombre"],"mesero")
        self.assertEqual(actual["preparado_por_nombre"],"cocina")
        self.assertEqual(actual["entregado_por_nombre"],"mesero")
        self.assertTrue(actual["en_preparacion_en"] and actual["listo_en"] and actual["entregado_en"])

    def test_stock_terminado_se_reserva_y_no_se_descuenta_al_pagar(self):
        p = self.crear(cantidad=2)
        self.pan.refresh_from_db(); self.assertEqual(self.pan.stock,8)
        self.entregar(p); self.pagar(p)
        self.pan.refresh_from_db(); self.assertEqual(self.pan.stock,8)

    def test_preparable_disponibilidad_por_receta_y_consumo_en_preparacion(self):
        self.assertEqual(self.cafe.stock_disponible,5)
        p = self.crear(self.cafe,2)
        self.leche.refresh_from_db(); self.assertEqual(self.leche.cantidad_stock,1000)
        self.assertEqual(self.cafe.stock_disponible,3)
        self.assertEqual(ReservaInsumo.objects.get(pedido_id=p["id"]).cantidad,400)
        self.avanzar(p,"EN_PREPARACION")
        self.leche.refresh_from_db(); self.assertEqual(self.leche.cantidad_stock,600)
        self.assertEqual(ReservaInsumo.objects.get(pedido_id=p["id"]).estado,"CONSUMIDA")
        self.assertEqual(self.cafe.stock_disponible,3)

    def test_reservas_impiden_sobreventa_de_insumo_compartido(self):
        self.crear(self.cafe,4)
        res=self.client.post("/api/pedidos/",{"mesa":1,"detalles":[{"producto":self.cafe.pk,"cantidad":2}]},format="json")
        self.assertEqual(res.status_code,400)
        self.assertEqual(Pedido.objects.count(),1)

    def test_lineas_repetidas_se_agrupan_y_no_manipulan_precio(self):
        res=self.client.post("/api/pedidos/",{"mesa":1,"detalles":[{"producto":self.pan.pk,"cantidad":2,"precio_unitario":"0.01"},{"producto":self.pan.pk,"cantidad":3}]},format="json")
        self.assertEqual(res.status_code,201,res.data)
        self.assertEqual(res.data["total"],"17.50")
        self.assertEqual(len(res.data["detalles"]),1)

    def test_stock_insuficiente_no_crea_pedido(self):
        res=self.client.post("/api/pedidos/",{"mesa":1,"detalles":[{"producto":self.pan.pk,"cantidad":11}]},format="json")
        self.assertEqual(res.status_code,400); self.assertFalse(Pedido.objects.exists())

    def test_atributos_invalidos(self):
        for mesa in [0,11,"abc"]:
            res=self.client.post("/api/pedidos/",{"mesa":mesa,"detalles":[{"producto":self.pan.pk,"cantidad":1}]},format="json")
            self.assertEqual(res.status_code,400)
        for cantidad in [0,-1,"1.5"]:
            res=self.client.post("/api/pedidos/",{"mesa":1,"detalles":[{"producto":self.pan.pk,"cantidad":cantidad}]},format="json")
            self.assertEqual(res.status_code,400)

    def test_cancelacion_antes_de_preparar_libera_reservas_una_vez(self):
        p=self.crear(self.cafe,2)
        r=self.client.post(f"/api/pedidos/{p['id']}/cancelar/",{"motivo":"Cliente se retiró"},format="json")
        self.assertEqual(r.status_code,200,r.data)
        self.assertEqual(self.cafe.stock_disponible,5)
        self.assertEqual(ReservaInsumo.objects.get(pedido_id=p["id"]).estado,"LIBERADA")
        self.assertEqual(self.client.post(f"/api/pedidos/{p['id']}/cancelar/",{"motivo":"Duplicado"},format="json").status_code,400)

    def test_cancelacion_producto_terminado_restituye_stock(self):
        p=self.crear(cantidad=2)
        self.client.post(f"/api/pedidos/{p['id']}/cancelar/",{"motivo":"Error"},format="json")
        self.pan.refresh_from_db(); self.assertEqual(self.pan.stock,10)

    def test_cancelacion_despues_de_preparar_no_repone_consumido(self):
        p=self.crear(self.cafe,2); self.avanzar(p,"EN_PREPARACION")
        r=self.client.post(f"/api/pedidos/{p['id']}/cancelar/",{"motivo":"Ya no lo desea"},format="json")
        self.assertEqual(r.status_code,200)
        self.leche.refresh_from_db(); self.assertEqual(self.leche.cantidad_stock,600)

    def test_no_doble_pago_y_no_doble_reembolso(self):
        p=self.crear(); self.entregar(p); pago=self.pagar(p)
        r=self.client.post("/api/pagos/",{"pedido":p["id"],"monto":p["total"],"metodo":"EFECTIVO"},format="json")
        self.assertEqual(r.status_code,400)
        url=f"/api/pagos/{pago['id']}/reembolsar/"
        self.assertEqual(self.client.post(url,{"motivo":"Reclamo"},format="json").status_code,200)
        self.assertEqual(self.client.post(url,{"motivo":"Reclamo"},format="json").status_code,400)
        self.pan.refresh_from_db(); self.assertEqual(self.pan.stock,9)
        self.assertEqual(Reembolso.objects.count(),1)

    def test_yape_pendiente_y_confirmacion_idempotente_notifica_una_vez(self):
        p=self.crear(); self.entregar(p); pago=self.pagar(p,"QR")
        self.assertEqual(pago["estado"],"PENDIENTE")
        self.assertFalse(Notificacion.objects.filter(tipo="PAGO_REALIZADO").exists())
        for _ in range(2):
            self.assertEqual(self.client.post(f"/api/pagos/{pago['id']}/confirmar/").status_code,200)
        self.assertEqual(Notificacion.objects.filter(tipo="PAGO_REALIZADO").count(),1)
        self.assertIn("Pago realizado",self.client.get("/api/notificaciones/").data[-1]["mensaje"])

    def test_yape_deshabilitado(self):
        ConfiguracionPago.objects.create(pk=1,qr_habilitado=False)
        p=self.crear(); self.entregar(p)
        res=self.client.post("/api/pagos/",{"pedido":p["id"],"monto":p["total"],"metodo":"QR","referencia_qr":"YAPE-1"},format="json")
        self.assertEqual(res.status_code,400)

    def test_montos_invalidos_yape_y_efectivo(self):
        p=self.crear(); self.entregar(p)
        for extra in [{"monto":"0"},{"monto":"1.00"},{"monto_recibido":"1"},{"monto":"NaN"},{"monto_recibido":"5.555"}]:
            r=self.client.post("/api/pagos/",{"pedido":p["id"],"monto":p["total"],"metodo":"EFECTIVO",**extra},format="json")
            self.assertEqual(r.status_code,400)
        r=self.client.post("/api/pagos/",{"pedido":p["id"],"monto":p["total"],"metodo":"QR"},format="json")
        self.assertEqual(r.status_code,400)

    def test_cambiar_pedido_relaciona_original_y_nuevo(self):
        p=self.crear(cantidad=2)
        r=self.client.post(f"/api/pedidos/{p['id']}/cambiar/",{"motivo":"Cambió de elección","detalles":[{"producto":self.cafe.pk,"cantidad":1}]},format="json")
        self.assertEqual(r.status_code,201,r.data)
        self.assertEqual(r.data["pedido_original"],p["id"])
        self.assertEqual(Pedido.objects.get(pk=p["id"]).estado,"CANCELADO")
        self.pan.refresh_from_db(); self.assertEqual(self.pan.stock,10)

    def test_cambio_invalido_revierte_original_y_reservas(self):
        p=self.crear(cantidad=2)
        r=self.client.post(f"/api/pedidos/{p['id']}/cambiar/",{"motivo":"Cambio","detalles":[{"producto":self.cafe.pk,"cantidad":99}]},format="json")
        self.assertEqual(r.status_code,400)
        self.assertEqual(Pedido.objects.get(pk=p["id"]).estado,"ESPERA")
        self.pan.refresh_from_db(); self.assertEqual(self.pan.stock,8)

    def test_cambio_pagado_reembolsa_y_conserva_historial(self):
        p=self.crear(); self.entregar(p); pago=self.pagar(p)
        r=self.client.post(f"/api/pedidos/{p['id']}/cambiar/",{"motivo":"Reclamo","detalles":[{"producto":self.cafe.pk,"cantidad":1}]},format="json")
        self.assertEqual(r.status_code,201,r.data)
        self.assertEqual(Pago.objects.get(pk=pago["id"]).estado,"REEMBOLSADO")
        self.assertEqual(Pedido.objects.get(pk=p["id"]).estado,"ENTREGADO")

    def test_permisos_por_rol(self):
        for rol in ["mesero","cocina"]:
            self.rol(rol)
            for url in ["/api/pagos/","/api/usuarios/","/api/insumos/","/api/reportes/"]:
                self.assertEqual(self.client.get(url).status_code,403,(rol,url))
        self.rol("cocina")
        self.assertEqual(self.client.post("/api/pedidos/",{},format="json").status_code,403)

    def test_transiciones_protegen_roles_y_orden(self):
        p=self.crear(); self.rol("mesero")
        self.assertEqual(self.client.patch(f"/api/pedidos/{p['id']}/estado/",{"estado":"EN_PREPARACION"},format="json").status_code,403)
        self.rol("cocina")
        self.assertEqual(self.client.patch(f"/api/pedidos/{p['id']}/estado/",{"estado":"ENTREGADO"},format="json").status_code,400)

    def test_no_edicion_arbitraria_ni_borrado_de_historial(self):
        p=self.crear()
        self.assertEqual(self.client.patch(f"/api/pedidos/{p['id']}/",{"estado":"ENTREGADO"},format="json").status_code,400)
        self.assertEqual(self.client.delete(f"/api/pedidos/{p['id']}/").status_code,405)

    def test_seguimiento_fecha_local_y_url_con_id_entero(self):
        p=self.crear(); hoy=timezone.localdate()
        self.assertEqual(len(self.client.get(f"/api/pedidos/?fecha={hoy}").data),1)
        self.assertEqual(self.client.get(f"/api/pedidos/?fecha={hoy-timedelta(days=1)}").data,[])
        self.assertEqual(self.client.get("/api/pedidos/?fecha=2026-99-99").status_code,400)
        self.assertEqual(self.client.get("/api/pedidos/no-id/").status_code,404)
        self.assertEqual(resolve(reverse("reporte-pdf",kwargs={"pk":3})).kwargs["pk"],3)

    def test_reporte_conciliacion_separa_efectivo_y_yape(self):
        p=self.crear(); self.entregar(p); self.pagar(p)
        q=self.crear(self.cafe); self.entregar(q); pago=self.pagar(q,"QR")
        self.client.post(f"/api/pagos/{pago['id']}/confirmar/")
        r=self.client.post("/api/pagos/conciliacion/",{"fecha":timezone.localdate().isoformat(),"efectivo_real":"3.50","qr_real":"7.00"},format="json")
        self.assertEqual(r.status_code,200,r.data)
        self.assertTrue(r.data["cuadra"])
        self.assertEqual(r.data["total_neto"],"10.50")
        self.assertEqual(r.data["por_metodo"]["qr"]["ventas"],"7.00")

    def test_reembolso_cuenta_en_su_fecha_y_pdf_es_inmutable(self):
        p=self.crear(); self.entregar(p); pago=self.pagar(p)
        ayer=timezone.now()-timedelta(days=1)
        Pago.objects.filter(pk=pago["id"]).update(pagado_en=ayer)
        self.client.post(f"/api/pagos/{pago['id']}/reembolsar/",{"motivo":"Devolución"},format="json")
        dia=timezone.localdate().isoformat()
        r=self.client.get(f"/api/pagos/reporte-ventas/?desde={dia}&hasta={dia}")
        self.assertEqual(r.data["total_ventas"],"0.00")
        self.assertEqual(r.data["total_reembolsos"],"3.50")
        pdf=self.client.post("/api/reportes/",{"tipo":"VENTAS","desde":dia,"hasta":dia},format="json")
        self.assertEqual(pdf.status_code,201,pdf.data)
        archivo=self.client.get(pdf.data["url"])
        self.assertEqual(archivo["Content-Type"],"application/pdf")
        self.assertTrue(archivo.content.startswith(b"%PDF-"))
        self.assertEqual(hashlib.sha256(archivo.content).hexdigest(),pdf.data["sha256"])
        Reembolso.objects.all().update(importe_reembolsado="1")
        self.assertEqual(self.client.get(pdf.data["url"]).content,archivo.content)

    def test_reporte_de_reportes_pdf(self):
        dia=timezone.localdate().isoformat()
        self.client.post("/api/reportes/",{"tipo":"VENTAS","desde":dia,"hasta":dia},format="json")
        r=self.client.post("/api/reportes/",{"tipo":"HISTORIAL","desde":dia,"hasta":dia},format="json")
        self.assertEqual(r.status_code,201,r.data)
        self.assertEqual(r.data["resumen"]["cantidad_reportes"],1)
        self.assertEqual(len(self.client.get(f"/api/reportes/?desde={dia}&hasta={dia}").data),2)

    def test_cajero_no_accede_reportes_historicos_ni_ajustes(self):
        self.rol("cajero")
        self.assertEqual(self.client.get("/api/reportes/?desde=2020-01-01&hasta=2020-01-01").status_code,403)
        self.assertEqual(self.client.patch("/api/configuracion-pago/",{"qr_habilitado":False},format="json").status_code,403)

    def test_imagen_obligatoria_receta_obligatoria_y_baja_logica(self):
        datos={"nombre":"Nuevo","categoria":self.cat.pk,"precio":"5.00","stock":2}
        self.assertEqual(self.client.post("/api/productos/",datos,format="json").status_code,400)
        datos.update(imagen="/images/productos/pan.jpg",preparable=True)
        self.assertEqual(self.client.post("/api/productos/",datos,format="json").status_code,400)
        datos["insumos"]=[{"insumo":self.leche.pk,"cantidad_insumo_por_unidad":"100"}]
        r=self.client.post("/api/productos/",datos,format="json"); self.assertEqual(r.status_code,201,r.data)
        self.assertEqual(r.data["stock_disponible"],10)
        self.assertEqual(self.client.delete(f"/api/productos/{self.pan.pk}/").status_code,204)
        self.pan.refresh_from_db(); self.assertFalse(self.pan.activo)
        self.rol("mesero"); self.assertNotIn(self.pan.pk,[p["id"] for p in self.client.get("/api/productos/").data["results"]])

    def test_editar_insumo_respeta_reservas(self):
        self.crear(self.cafe,3)
        r=self.client.patch(f"/api/insumos/{self.leche.pk}/",{"cantidad_stock":"500"},format="json")
        self.assertEqual(r.status_code,400)

    def test_subir_imagen_valida_y_rechazar_archivo_que_no_es_imagen(self):
        salida=BytesIO()
        Image.new("RGB",(2,2),"white").save(salida,format="PNG")
        with tempfile.TemporaryDirectory() as directorio, override_settings(MEDIA_ROOT=directorio):
            archivo=SimpleUploadedFile("producto.png",salida.getvalue(),content_type="image/png")
            res=self.client.post("/api/imagenes/",{"imagen":archivo},format="multipart")
            self.assertEqual(res.status_code,201,res.data)
            self.assertTrue(res.data["imagen"].startswith("/media/productos/"))
            falso=SimpleUploadedFile("falso.png",b"no es una imagen",content_type="image/png")
            self.assertEqual(self.client.post("/api/imagenes/",{"imagen":falso},format="multipart").status_code,400)

    @override_settings(QR_WEBHOOK_SECRET="secreto-prueba")
    def test_webhook_firma_monto_y_reintentos(self):
        p=self.crear(); self.entregar(p); pago=self.pagar(p,"QR")
        datos={"evento":"yape-evento-1","pago_id":pago["id"],"monto":p["total"],"estado":"COMPLETADO","referencia_qr":"YAPE-0001"}
        cuerpo=json.dumps(datos).encode()
        firma=hmac.new(b"secreto-prueba",cuerpo,hashlib.sha256).hexdigest()
        anonimo=APIClient()
        self.assertEqual(anonimo.post("/api/pagos/webhook-qr/",cuerpo,content_type="application/json").status_code,403)
        for _ in range(2):
            r=anonimo.post("/api/pagos/webhook-qr/",cuerpo,content_type="application/json",HTTP_X_QR_SIGNATURE=firma)
            self.assertEqual(r.status_code,200,r.data)
        self.assertEqual(Notificacion.objects.filter(tipo="PAGO_REALIZADO").count(),1)

    def test_webhook_desactivado_sin_integracion(self):
        self.assertEqual(APIClient().post("/api/pagos/webhook-qr/",{},format="json").status_code,503)
