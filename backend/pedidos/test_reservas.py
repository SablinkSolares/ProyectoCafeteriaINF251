from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from threading import Barrier

from django.contrib.auth import get_user_model
from django.db import connections
from django.test import TransactionTestCase
from rest_framework.test import APITestCase, APIClient

from catalogo.models import Categoria, Insumo, Producto, ProductoInsumo
from .models import Pedido, Pago, ReservaInsumo


class FlujoReservasTests(APITestCase):
    def setUp(self):
        User = get_user_model()
        self.admin = User.objects.create_user(username="admin_reserva", password="x", rol="administrador")
        self.mesero = User.objects.create_user(username="mesero_reserva", password="x", rol="mesero")
        self.cajero = User.objects.create_user(username="cajero_reserva", password="x", rol="cajero")
        categoria = Categoria.objects.create(nombre="Bebidas")
        self.cafe = Producto.objects.create(nombre="Café", categoria=categoria, precio=7, stock=10)
        self.insumo = Insumo.objects.create(nombre_insumo="Cápsulas", unidad_medida="unidades", cantidad_stock=5)
        self.receta = ProductoInsumo.objects.create(producto=self.cafe, insumo=self.insumo, cantidad_insumo_por_unidad=2)
        self.client.force_authenticate(self.mesero)

    def crear(self, cantidad):
        return self.client.post("/api/pedidos/", {"detalles": [{"producto": self.cafe.pk, "cantidad": cantidad}]}, format="json")

    def entregar(self, pedido_id):
        self.client.force_authenticate(self.admin)
        for estado in ("EN_PREPARACION", "LISTO", "ENTREGADO"):
            respuesta = self.client.patch(f"/api/pedidos/{pedido_id}/estado/", {"estado": estado}, format="json")
            self.assertEqual(respuesta.status_code, 200, respuesta.data)

    def pagar(self, pedido_id, monto, metodo="EFECTIVO"):
        self.client.force_authenticate(self.cajero)
        return self.client.post("/api/pagos/", {"pedido": pedido_id, "monto": monto, "metodo": metodo}, format="json")

    def test_reserva_no_descuenta_insumo_y_protege_otros_pedidos(self):
        primero = self.crear(2)
        self.assertEqual(primero.status_code, 201, primero.data)
        self.insumo.refresh_from_db(); self.cafe.refresh_from_db()
        self.assertEqual(self.insumo.cantidad_stock, Decimal("5"))
        self.assertEqual(self.cafe.stock, Decimal("8"))
        reserva = ReservaInsumo.objects.get(pedido_id=primero.data["id"])
        self.assertEqual((reserva.cantidad, reserva.estado), (Decimal("4"), "RESERVADA"))
        segundo = self.crear(1)
        self.assertEqual(segundo.status_code, 400)
        self.assertIn("Cápsulas", str(segundo.data))
        self.cafe.refresh_from_db()
        self.assertEqual(self.cafe.stock, Decimal("8"))
        self.assertEqual(Pedido.objects.count(), 1)

    def test_pago_solo_tras_entrega_y_consume_la_receta_reservada(self):
        respuesta = self.crear(2); pid = respuesta.data["id"]
        self.assertEqual(self.pagar(pid, "14.00").status_code, 400)
        self.assertFalse(Pago.objects.filter(pedido_id=pid).exists())
        self.receta.cantidad_insumo_por_unidad = 1
        self.receta.save()
        self.entregar(pid)
        self.assertEqual(self.pagar(pid, "14.00").status_code, 201)
        self.insumo.refresh_from_db()
        self.assertEqual(self.insumo.cantidad_stock, Decimal("1"))
        self.assertEqual(ReservaInsumo.objects.get(pedido_id=pid).estado, "CONSUMIDA")
        self.assertEqual(self.pagar(pid, "14.00").status_code, 400)
        self.insumo.refresh_from_db()
        self.assertEqual(self.insumo.cantidad_stock, Decimal("1"))

    def test_qr_pendiente_retiene_reserva_hasta_confirmar(self):
        pid = self.crear(2).data["id"]
        self.entregar(pid)
        pago = self.pagar(pid, "14.00", "QR")
        self.assertEqual(pago.status_code, 201)
        self.insumo.refresh_from_db()
        self.assertEqual(self.insumo.cantidad_stock, Decimal("5"))
        self.assertEqual(ReservaInsumo.objects.get(pedido_id=pid).estado, "RESERVADA")
        self.assertEqual(self.client.post(f"/api/pagos/{pago.data['id']}/confirmar/").status_code, 200)
        self.insumo.refresh_from_db()
        self.assertEqual(self.insumo.cantidad_stock, Decimal("1"))

    def test_cancelar_libera_producto_e_insumo_una_sola_vez(self):
        pid = self.crear(2).data["id"]
        res = self.client.post(f"/api/pedidos/{pid}/cancelar/")
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual(res.data["estado"], "CANCELADO")
        self.assertEqual(ReservaInsumo.objects.get(pedido_id=pid).estado, "LIBERADA")
        self.cafe.refresh_from_db(); self.insumo.refresh_from_db()
        self.assertEqual(self.cafe.stock, Decimal("10")); self.assertEqual(self.insumo.cantidad_stock, Decimal("5"))
        self.assertEqual(self.client.post(f"/api/pedidos/{pid}/cancelar/").status_code, 400)
        self.assertEqual(self.crear(2).status_code, 201)

    def test_sin_receta_se_puede_pedir_y_legacy_no_se_cancela_sin_revision(self):
        self.receta.delete()
        self.assertEqual(self.crear(1).status_code, 201)
        antiguo = Pedido.objects.create()
        self.assertEqual(self.client.post(f"/api/pedidos/{antiguo.pk}/cancelar/").status_code, 400)

    def test_reembolso_tras_entrega_no_repone_productos_ni_insumos(self):
        pid = self.crear(2).data["id"]
        self.entregar(pid)
        pago = self.pagar(pid, "14.00")
        self.assertEqual(self.client.post(f"/api/pagos/{pago.data['id']}/reembolsar/", {"motivo": "Prueba"}, format="json").status_code, 200)
        self.cafe.refresh_from_db(); self.insumo.refresh_from_db()
        self.assertEqual(self.cafe.stock, Decimal("8")); self.assertEqual(self.insumo.cantidad_stock, Decimal("1"))


class ReservasConcurrentesTests(TransactionTestCase):
    def test_no_se_reserva_dos_veces_el_mismo_insumo(self):
        User = get_user_model()
        user = User.objects.create_user(username="concurrencia", password="x", rol="mesero")
        cat = Categoria.objects.create(nombre="Café simultáneo")
        producto = Producto.objects.create(nombre="Bebida", categoria=cat, precio=7, stock=2)
        insumo = Insumo.objects.create(nombre_insumo="Última cápsula", unidad_medida="unidad", cantidad_stock=1)
        ProductoInsumo.objects.create(producto=producto, insumo=insumo, cantidad_insumo_por_unidad=1)
        barrera = Barrier(2)
        def pedir():
            try:
                cliente = APIClient(); cliente.force_authenticate(user=user)
                barrera.wait(timeout=15)
                return cliente.post("/api/pedidos/", {"detalles": [{"producto": producto.pk, "cantidad": 1}]}, format="json").status_code
            finally:
                connections.close_all()
        with ThreadPoolExecutor(max_workers=2) as pool:
            resultados = list(pool.map(lambda _: pedir(), range(2)))
        self.assertEqual(sorted(resultados), [201, 400])
        self.assertEqual(ReservaInsumo.objects.filter(estado="RESERVADA").count(), 1)
