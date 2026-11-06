from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APITestCase

from catalogo.models import Categoria, Insumo, Producto, ProductoInsumo
from .models import DetallePedido, Pago, Pedido, Reembolso


class VentasEInsumosTests(APITestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_user(username="administrador", password="x", rol="administrador")
        self.cajero = get_user_model().objects.create_user(username="cajero", password="x", rol="cajero")
        self.client.force_authenticate(self.cajero)
        self.categoria = Categoria.objects.create(nombre="Bebidas")
        self.cafe = Producto.objects.create(nombre="Café", categoria=self.categoria, precio=Decimal("7.00"), stock=10)
        self.azucar = Insumo.objects.create(nombre_insumo="Azúcar", unidad_medida="sobres", cantidad_stock=10)
        self.capsula = Insumo.objects.create(nombre_insumo="Cápsula", unidad_medida="unidades", cantidad_stock=3)
        ProductoInsumo.objects.create(producto=self.cafe, insumo=self.azucar, cantidad_insumo_por_unidad=2)
        ProductoInsumo.objects.create(producto=self.cafe, insumo=self.capsula, cantidad_insumo_por_unidad=1)

    def pedido(self, cantidades=(2,)):
        pedido = Pedido.objects.create(estado=Pedido.Estado.ENTREGADO)
        for cantidad in cantidades:
            DetallePedido.objects.create(pedido=pedido, producto=self.cafe, cantidad=cantidad, precio_unitario=Decimal("7.00"))
        return pedido

    def pagar(self, pedido, metodo="EFECTIVO"):
        return self.client.post("/api/pagos/", {"pedido": pedido.pk, "monto": str(pedido.total), "metodo": metodo}, format="json")

    def test_efectivo_descontado_una_vez_agrupando_lineas(self):
        pedido = self.pedido((1, 1))
        respuesta = self.pagar(pedido)
        self.assertEqual(respuesta.status_code, 201, respuesta.data)
        self.azucar.refresh_from_db()
        self.capsula.refresh_from_db()
        self.assertEqual(self.azucar.cantidad_stock, Decimal("6"))
        self.assertEqual(self.capsula.cantidad_stock, Decimal("1"))
        self.assertEqual(self.pagar(pedido).status_code, 400)
        self.azucar.refresh_from_db()
        self.assertEqual(self.azucar.cantidad_stock, Decimal("6"))

    def test_qr_solo_descuenta_al_confirmar_y_no_dos_veces(self):
        respuesta = self.pagar(self.pedido(), "QR")
        self.assertEqual(respuesta.status_code, 201)
        self.azucar.refresh_from_db()
        self.assertEqual(self.azucar.cantidad_stock, Decimal("10"))
        url = f"/api/pagos/{respuesta.data['id']}/confirmar/"
        self.assertEqual(self.client.post(url).status_code, 200)
        self.assertEqual(self.client.post(url).status_code, 400)
        self.azucar.refresh_from_db()
        self.assertEqual(self.azucar.cantidad_stock, Decimal("6"))

    def test_faltantes_bloquean_pago_sin_descontar_ningun_insumo(self):
        pedido = self.pedido((4,))
        respuesta = self.pagar(pedido)
        self.assertEqual(respuesta.status_code, 400)
        self.assertIn("Cápsula", str(respuesta.data))
        self.assertFalse(Pago.objects.filter(pedido=pedido).exists())
        self.azucar.refresh_from_db()
        self.capsula.refresh_from_db()
        self.assertEqual(self.azucar.cantidad_stock, Decimal("10"))
        self.assertEqual(self.capsula.cantidad_stock, Decimal("3"))

    def test_qr_faltantes_permanece_pendiente_y_reintento_funciona(self):
        respuesta = self.pagar(self.pedido((4,)), "QR")
        pago = Pago.objects.get(pk=respuesta.data["id"])
        url = f"/api/pagos/{pago.pk}/confirmar/"
        self.assertEqual(self.client.post(url).status_code, 400)
        pago.refresh_from_db()
        self.assertEqual(pago.estado, Pago.Estado.PENDIENTE)
        self.assertIsNone(pago.pagado_en)
        self.capsula.cantidad_stock = 5
        self.capsula.save()
        self.assertEqual(self.client.post(url).status_code, 200)
        self.azucar.refresh_from_db()
        self.assertEqual(self.azucar.cantidad_stock, Decimal("2"))

    def test_producto_sin_receta_se_puede_cobrar_y_reembolso_no_repone_insumos(self):
        respuesta = self.pagar(self.pedido())
        self.assertEqual(self.client.post(f"/api/pagos/{respuesta.data['id']}/reembolsar/", {"motivo": "Prueba"}, format="json").status_code, 200)
        self.azucar.refresh_from_db()
        self.assertEqual(self.azucar.cantidad_stock, Decimal("6"))
        ProductoInsumo.objects.all().delete()
        self.assertEqual(self.pagar(self.pedido()).status_code, 201)

    def test_reporte_fechas_agrupa_ventas_y_reembolsos_por_su_fecha(self):
        pedido = self.pedido()
        pago = Pago.objects.create(pedido=pedido, monto=pedido.total, metodo="EFECTIVO", estado="REEMBOLSADO", pagado_en=datetime(2026, 1, 10, 12, tzinfo=ZoneInfo("America/La_Paz")))
        Reembolso.objects.create(pago=pago, importe_reembolsado=pago.monto, fecha_hora_reembolso=datetime(2026, 1, 11, 12, tzinfo=ZoneInfo("America/La_Paz")))
        self.client.force_authenticate(self.admin)
        res = self.client.get("/api/pagos/reporte-ventas/?desde=2026-01-10&hasta=2026-01-10")
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual(res.data["total_ventas"], "14.00")
        self.assertEqual(res.data["total_reembolsos"], "0.00")
        self.assertEqual(res.data["productos"][0]["unidades"], 2)
        self.assertEqual(res.data["categorias"][0]["total"], Decimal("14.00"))
        siguiente = self.client.get("/api/pagos/reporte-ventas/?desde=2026-01-11&hasta=2026-01-11")
        self.assertEqual(siguiente.data["total_neto"], "-14.00")
        self.assertEqual(siguiente.data["productos"], [])

    def test_reporte_solo_admin_y_fechas_validas(self):
        url = "/api/pagos/reporte-ventas/?desde=2026-01-01&hasta=2026-01-31"
        self.assertEqual(self.client.get(url).status_code, 403)
        self.client.force_authenticate(self.admin)
        self.assertEqual(self.client.get("/api/pagos/reporte-ventas/?desde=2026-02-31&hasta=2026-01-01").status_code, 400)
        self.assertEqual(self.client.get("/api/pagos/reporte-ventas/?desde=2026-02-01&hasta=2026-01-01").status_code, 400)
