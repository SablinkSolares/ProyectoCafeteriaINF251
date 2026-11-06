from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status
from datetime import datetime, timedelta
from django.utils import timezone
from .models import Pedido, Pago
from catalogo.models import Categoria, Producto
from decimal import Decimal

User = get_user_model()


class AutenticacionTests(APITestCase):

    def setUp(self):
        self.usuario = User.objects.create_user(
            username="cajero_test",
            password="Test12345",
            rol="cajero"
        )

    def test_login_correcto(self):
        respuesta = self.client.post(
            "/api/auth/login/",
            {
                "username": "cajero_test",
                "password": "Test12345"
            },
            format="json"
        )

        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertIn("access", respuesta.data)
        self.assertIn("refresh", respuesta.data)
        self.assertEqual(respuesta.data["rol"], "cajero")




class PedidoTests(APITestCase):
    def test_administrador_no_puede_saltar_estados_editando_pedido(self):
        administrador = User.objects.create_user(
            username="admin_test",
            password="Test12345",
            rol="administrador"
        )

        pedido_id = self.crear_pedido()
        self.client.force_authenticate(user=administrador)

        respuesta = self.client.patch(
            f"/api/pedidos/{pedido_id}/",
            {"estado": "EN_PREPARACION"},
            format="json"
        )

        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)

    def test_administrador_puede_eliminar_pedido(self):
        administrador = User.objects.create_user(
            username="admin_delete_test",
            password="Test12345",
            rol="administrador"
        )

        pedido_id = self.crear_pedido()
        self.client.force_authenticate(user=administrador)

        respuesta = self.client.delete(
            f"/api/pedidos/{pedido_id}/"
        )

        self.assertEqual(respuesta.status_code, status.HTTP_204_NO_CONTENT)

    def test_mesero_no_puede_editar_pedido(self):
        pedido_id = self.crear_pedido()

        respuesta = self.client.patch(
            f"/api/pedidos/{pedido_id}/",
            {"estado": "EN_PREPARACION"},
            format="json"
        )

        self.assertEqual(
            respuesta.status_code,
            status.HTTP_403_FORBIDDEN
        )

    def test_pedido_entregado_no_admite_mas_cambios(self):
        pedido_id = self.crear_pedido()

        pedido = Pedido.objects.get(pk=pedido_id)
        pedido.estado = Pedido.Estado.ENTREGADO
        pedido.save()

        respuesta = self.client.patch(
            f"/api/pedidos/{pedido_id}/estado/",
            {"estado": "ESPERA"},
            format="json"
        )

        self.assertEqual(
            respuesta.status_code,
            status.HTTP_400_BAD_REQUEST
        )

    def test_filtrar_pedidos_por_estado(self):
        pedido_id = self.crear_pedido()

        respuesta = self.client.get(
            "/api/pedidos/?estado=ESPERA"
        )

        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertEqual(len(respuesta.data), 1)
        self.assertEqual(respuesta.data[0]["estado"], "ESPERA")

    def test_filtro_no_devuelve_pedidos_de_otro_estado(self):
        self.crear_pedido()

        respuesta = self.client.get(
            "/api/pedidos/?estado=ENTREGADO"
        )

        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertEqual(len(respuesta.data), 0)

    def test_listar_pedidos(self):
        self.crear_pedido()

        respuesta = self.client.get("/api/pedidos/")

        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertEqual(len(respuesta.data), 1)

    def test_consultar_detalle_pedido(self):
        pedido_id = self.crear_pedido()

        respuesta = self.client.get(
            f"/api/pedidos/{pedido_id}/"
        )

        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertEqual(respuesta.data["id"], pedido_id)

    def test_mesero_no_puede_eliminar_pedido(self):
        pedido_id = self.crear_pedido()

        respuesta = self.client.delete(
            f"/api/pedidos/{pedido_id}/"
        )

        self.assertEqual(
            respuesta.status_code,
            status.HTTP_403_FORBIDDEN
        )

    def crear_pedido(self):
        pedido = Pedido.objects.create()

        from .models import DetallePedido

        DetallePedido.objects.create(
            pedido=pedido,
            producto=self.producto,
            cantidad=1,
            precio_unitario=self.producto.precio
        )

        return pedido.id
    def test_mesero_no_puede_cambiar_a_preparacion(self):
        pedido_id = self.crear_pedido()

        respuesta = self.client.patch(
            f"/api/pedidos/{pedido_id}/estado/",
            {"estado": "EN_PREPARACION"},
            format="json"
        )

        self.assertEqual(
            respuesta.status_code,
            status.HTTP_403_FORBIDDEN
        )

    def test_cocina_puede_cambiar_a_preparacion(self):
        cocina = User.objects.create_user(
            username="cocina_test",
            password="Test12345",
            rol="cocina"
        )

        pedido_id = self.crear_pedido()
        self.client.force_authenticate(user=cocina)

        respuesta = self.client.patch(
            f"/api/pedidos/{pedido_id}/estado/",
            {"estado": "EN_PREPARACION"},
            format="json"
        )

        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertEqual(respuesta.data["estado"], "EN_PREPARACION")

    def test_rechazar_transicion_incorrecta(self):
        cocina = User.objects.create_user(
            username="cocina_transicion_test",
            password="Test12345",
            rol="cocina"
        )

        pedido_id = self.crear_pedido()

        self.client.force_authenticate(user=cocina)

        respuesta = self.client.patch(
            f"/api/pedidos/{pedido_id}/estado/",
            {"estado": "LISTO"},
            format="json"
        )

        self.assertEqual(
            respuesta.status_code,
            status.HTTP_400_BAD_REQUEST
        )

    def test_mesero_puede_entregar_pedido_listo(self):
        pedido_id = self.crear_pedido()

        pedido = Pedido.objects.get(pk=pedido_id)
        pedido.estado = Pedido.Estado.LISTO
        pedido.save()

        respuesta = self.client.patch(
            f"/api/pedidos/{pedido_id}/estado/",
            {"estado": "ENTREGADO"},
            format="json"
        )

        self.assertEqual(
            respuesta.status_code,
            status.HTTP_200_OK
        )
        self.assertEqual(respuesta.data["estado"], "ENTREGADO")

    def setUp(self):
        self.usuario = User.objects.create_user(
            username="mesero_test",
            password="Test12345",
            rol="mesero"
        )

        self.client.force_authenticate(user=self.usuario)

        self.categoria = Categoria.objects.create(
            nombre="Bebidas de prueba"
        )

        self.producto = Producto.objects.create(
            nombre="Café de prueba",
            categoria=self.categoria,
            precio=Decimal("15.00"),
            stock=10
        )

    def test_crear_pedido_correctamente(self):
        respuesta = self.client.post(
            "/api/pedidos/",
            {
                "detalles": [
                    {
                        "producto": self.producto.id,
                        "cantidad": 2
                    }
                ]
            },
            format="json"
        )

        self.assertEqual(respuesta.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Decimal(str(respuesta.data["total"])), Decimal("30.00"))
        self.assertEqual(len(respuesta.data["detalles"]), 1)

    def test_rechazar_pedido_sin_stock_suficiente(self):
        respuesta = self.client.post(
            "/api/pedidos/",
            {
                "detalles": [
                    {
                        "producto": self.producto.id,
                        "cantidad": 20
                    }
                ]
            },
            format="json"
        )

        self.assertEqual(
            respuesta.status_code,
            status.HTTP_400_BAD_REQUEST
        )
    
    def test_no_permitir_manipular_precio_desde_cliente(self):
        respuesta = self.client.post(
            "/api/pedidos/",
            {
                "detalles": [
                    {
                        "producto": self.producto.id,
                        "cantidad": 2,
                        "precio_unitario": "1.00"
                    }
                ]
            },
            format="json"
        )

        self.assertEqual(respuesta.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            Decimal(str(respuesta.data["total"])),
            Decimal("30.00")
        )
        self.assertEqual(
            Decimal(str(respuesta.data["detalles"][0]["precio_unitario"])),
            Decimal("15.00")
        )

    def test_calcular_total_con_varios_productos(self):
        segundo_producto = Producto.objects.create(
            nombre="Té de prueba",
            categoria=self.categoria,
            precio=Decimal("10.00"),
            stock=5
        )

        respuesta = self.client.post(
            "/api/pedidos/",
            {
                "detalles": [
                    {
                        "producto": self.producto.id,
                        "cantidad": 2
                    },
                    {
                        "producto": segundo_producto.id,
                        "cantidad": 3
                    }
                ]
            },
            format="json"
        )

        self.assertEqual(respuesta.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            Decimal(str(respuesta.data["total"])),
            Decimal("60.00")
        )

    def test_descontar_stock_al_crear_pedido(self):
        respuesta = self.client.post(
            "/api/pedidos/",
            {
                "detalles": [
                    {
                        "producto": self.producto.id,
                        "cantidad": 3
                    }
                ]
            },
            format="json"
        )

        self.assertEqual(respuesta.status_code, status.HTTP_201_CREATED)

        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock, 7)

    def test_rechazar_cantidad_cero(self):
        respuesta = self.client.post(
            "/api/pedidos/",
            {
                "detalles": [
                    {
                        "producto": self.producto.id,
                        "cantidad": 0
                    }
                ]
            },
            format="json"
        )

        self.assertEqual(
            respuesta.status_code,
            status.HTTP_400_BAD_REQUEST
        )

    def test_conservar_precio_historico_del_pedido(self):
        respuesta = self.client.post(
            "/api/pedidos/",
            {
                "detalles": [
                    {
                        "producto": self.producto.id,
                        "cantidad": 2
                    }
                ]
            },
            format="json"
        )

        self.assertEqual(respuesta.status_code, status.HTTP_201_CREATED)

        self.producto.precio = Decimal("25.00")
        self.producto.save()

        pedido = Pedido.objects.get(pk=respuesta.data["id"])

        self.assertEqual(
            pedido.detalles.first().precio_unitario,
            Decimal("15.00")
        )
        self.assertEqual(pedido.total, Decimal("30.00"))

    def test_rechazar_pedido_sin_detalles(self):
        cantidad_anterior = Pedido.objects.count()

        respuesta = self.client.post(
            "/api/pedidos/",
            {"detalles": []},
            format="json"
        )

        self.assertEqual(
            respuesta.status_code,
            status.HTTP_400_BAD_REQUEST
        )

        self.assertEqual(
            Pedido.objects.count(),
            cantidad_anterior
        )

    def test_producto_repetido_descuenta_stock_correctamente(self):
        respuesta = self.client.post(
            "/api/pedidos/",
            {
                "detalles": [
                    {
                        "producto": self.producto.id,
                        "cantidad": 3
                    },
                    {
                        "producto": self.producto.id,
                        "cantidad": 4
                    }
                ]
            },
            format="json"
        )

        self.assertEqual(
            respuesta.status_code,
            status.HTTP_201_CREATED
        )

        self.producto.refresh_from_db()

        self.assertEqual(self.producto.stock, 3)
        self.assertEqual(
            Decimal(str(respuesta.data["total"])),
            Decimal("105.00")
        )

    def test_producto_repetido_sin_stock_suficiente_no_crea_pedido(self):
        cantidad_anterior = Pedido.objects.count()

        respuesta = self.client.post(
            "/api/pedidos/",
            {
                "detalles": [
                    {
                        "producto": self.producto.id,
                        "cantidad": 6
                    },
                    {
                        "producto": self.producto.id,
                        "cantidad": 5
                    }
                ]
            },
            format="json"
        )

        self.assertEqual(
            respuesta.status_code,
            status.HTTP_400_BAD_REQUEST
        )

        self.assertEqual(
            Pedido.objects.count(),
            cantidad_anterior
        )

        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock, 10)

    def test_rechazar_producto_inexistente(self):
        respuesta = self.client.post(
            "/api/pedidos/",
            {
                "detalles": [
                    {
                        "producto": 999999,
                        "cantidad": 1
                    }
                ]
            },
            format="json"
        )

        self.assertEqual(
            respuesta.status_code,
            status.HTTP_400_BAD_REQUEST
        )

        self.assertEqual(Pedido.objects.count(), 0)



class PagoTests(APITestCase):

    def setUp(self):
        self.usuario = User.objects.create_user(
            username="cajero_pago_test",
            password="Test12345",
            rol="cajero"
        )

        self.client.force_authenticate(user=self.usuario)

        self.categoria = Categoria.objects.create(
            nombre="Bebidas para pagos"
        )

        # Stock de 8 porque simulamos que ya se vendieron 2 unidades.
        self.producto = Producto.objects.create(
            nombre="Café para pagos",
            categoria=self.categoria,
            precio=Decimal("20.00"),
            stock=8
        )

        self.pedido = Pedido.objects.create(estado=Pedido.Estado.ENTREGADO)

        from .models import DetallePedido

        DetallePedido.objects.create(
            pedido=self.pedido,
            producto=self.producto,
            cantidad=2,
            precio_unitario=Decimal("20.00")
        )

    def test_pago_efectivo_completado(self):
        respuesta = self.client.post(
            "/api/pagos/",
            {
                "pedido": self.pedido.id,
                "monto": "40.00",
                "metodo": "EFECTIVO"
            },
            format="json"
        )

        self.assertEqual(respuesta.status_code, status.HTTP_201_CREATED)
        self.assertEqual(respuesta.data["estado"], "COMPLETADO")
        self.assertIsNotNone(respuesta.data["pagado_en"])

    def test_pago_qr_pendiente(self):
        respuesta = self.client.post(
            "/api/pagos/",
            {
                "pedido": self.pedido.id,
                "monto": "40.00",
                "metodo": "QR",
                "referencia_qr": "QR-TEST-001"
            },
            format="json"
        )

        self.assertEqual(respuesta.status_code, status.HTTP_201_CREATED)
        self.assertEqual(respuesta.data["estado"], "PENDIENTE")

    def test_confirmar_pago_qr(self):
        pago = Pago.objects.create(
            pedido=self.pedido,
            monto=Decimal("40.00"),
            metodo=Pago.Metodo.QR,
            estado=Pago.Estado.PENDIENTE
        )

        respuesta = self.client.post(
            f"/api/pagos/{pago.id}/confirmar/",
            format="json"
        )

        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertEqual(respuesta.data["estado"], "COMPLETADO")

    def test_reembolsar_pago(self):
        pago = Pago.objects.create(
            pedido=self.pedido,
            monto=Decimal("40.00"),
            metodo=Pago.Metodo.EFECTIVO,
            estado=Pago.Estado.COMPLETADO
        )

        respuesta = self.client.post(
            f"/api/pagos/{pago.id}/reembolsar/",
            {"motivo": "Prueba de reembolso"},
            format="json"
        )

        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertEqual(respuesta.data["estado"], "REEMBOLSADO")
        self.assertEqual(
            respuesta.data["motivo_reembolso"],
            "Prueba de reembolso"
        )

        # Comprobar que las 2 unidades regresaron al inventario.
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock, 10)

    def test_no_reembolsar_dos_veces(self):
        pago = Pago.objects.create(
            pedido=self.pedido,
            monto=Decimal("40.00"),
            metodo=Pago.Metodo.EFECTIVO,
            estado=Pago.Estado.COMPLETADO
        )

        primera_respuesta = self.client.post(
            f"/api/pagos/{pago.id}/reembolsar/",
            {"motivo": "Primer reembolso"},
            format="json"
        )

        self.assertEqual(
            primera_respuesta.status_code,
            status.HTTP_200_OK
        )

        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock, 10)

        segunda_respuesta = self.client.post(
            f"/api/pagos/{pago.id}/reembolsar/",
            {"motivo": "Segundo reembolso"},
            format="json"
        )

        self.assertEqual(
            segunda_respuesta.status_code,
            status.HTTP_400_BAD_REQUEST
        )

        # El segundo intento no debe devolver más unidades.
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock, 10)

    def test_rechazar_pago_duplicado(self):
        Pago.objects.create(
            pedido=self.pedido,
            monto=Decimal("40.00"),
            metodo=Pago.Metodo.EFECTIVO,
            estado=Pago.Estado.COMPLETADO
        )

        respuesta = self.client.post(
            "/api/pagos/",
            {
                "pedido": self.pedido.id,
                "monto": "40.00",
                "metodo": "EFECTIVO"
            },
            format="json"
        )

        self.assertEqual(
            respuesta.status_code,
            status.HTTP_400_BAD_REQUEST
        )

    def test_rechazar_monto_incorrecto(self):
        respuesta = self.client.post(
            "/api/pagos/",
            {
                "pedido": self.pedido.id,
                "monto": "30.00",
                "metodo": "EFECTIVO"
            },
            format="json"
        )

        self.assertEqual(
            respuesta.status_code,
            status.HTTP_400_BAD_REQUEST
        )

    def test_mesero_no_puede_gestionar_pagos(self):
        mesero = User.objects.create_user(
            username="mesero_pago_test",
            password="Test12345",
            rol="mesero"
        )

        self.client.force_authenticate(user=mesero)

        respuesta = self.client.post(
            "/api/pagos/",
            {
                "pedido": self.pedido.id,
                "monto": "40.00",
                "metodo": "EFECTIVO"
            },
            format="json"
        )

        self.assertEqual(
            respuesta.status_code,
            status.HTTP_403_FORBIDDEN
        )

    def test_no_reembolsar_pago_pendiente(self):
        pago = Pago.objects.create(
            pedido=self.pedido,
            monto=Decimal("40.00"),
            metodo=Pago.Metodo.QR,
            estado=Pago.Estado.PENDIENTE
        )

        respuesta = self.client.post(
            f"/api/pagos/{pago.id}/reembolsar/",
            {"motivo": "Prueba de reembolso"},
            format="json"
        )

        self.assertEqual(
            respuesta.status_code,
            status.HTTP_400_BAD_REQUEST
        )

        # El stock debe permanecer en 8 porque no hubo reembolso.
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock, 8)

class ConciliacionTests(APITestCase):

    def setUp(self):
        self.usuario = User.objects.create_user(
            username="cajero_conciliacion",
            password="Test12345",
            rol="cajero"
        )

        self.client.force_authenticate(user=self.usuario)

        self.fecha = datetime(2026, 11, 3, 10, 0)

        self.fecha_anterior = self.fecha - timedelta(days=1)

        self.fecha = timezone.make_aware(self.fecha)
        self.fecha_anterior = timezone.make_aware(
            self.fecha_anterior
        )

    def crear_pago(
        self,
        monto,
        metodo,
        estado,
        pagado_en=None,
        reembolsado_en=None
    ):
        pedido = Pedido.objects.create()

        pago = Pago.objects.create(
            pedido=pedido,
            monto=Decimal(monto),
            metodo=metodo,
            estado=estado,
            pagado_en=pagado_en,
        )
        if reembolsado_en is not None:
            from .models import Reembolso
            Reembolso.objects.create(
                pago=pago, fecha_hora_reembolso=reembolsado_en,
                importe_reembolsado=Decimal(monto), tipo_reembolso="total",
            )
        return pago

    def test_conciliacion_ventas_por_metodo(self):

        self.crear_pago(
            "50.00",
            Pago.Metodo.EFECTIVO,
            Pago.Estado.COMPLETADO,
            self.fecha
        )

        self.crear_pago(
            "30.00",
            Pago.Metodo.QR,
            Pago.Estado.COMPLETADO,
            self.fecha
        )

        # Los pagos pendientes no deben contabilizarse.
        self.crear_pago(
            "20.00",
            Pago.Metodo.QR,
            Pago.Estado.PENDIENTE
        )

        respuesta = self.client.post(
            "/api/pagos/conciliacion/",
            {
                "fecha": "2026-11-03",
                "efectivo_real": "50.00",
                "qr_real": "30.00",
            },
            format="json"
        )

        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)

        self.assertEqual(
            respuesta.data["ventas"]["efectivo"]["total"],
            "50.00"
        )

        self.assertEqual(
            respuesta.data["ventas"]["qr"]["total"],
            "30.00"
        )

        self.assertEqual(respuesta.data["total_neto"], "80.00")
        self.assertTrue(respuesta.data["cuadra"])

    def test_reembolsos_se_descuentan_en_su_fecha(self):

        # Venta realizada y reembolsada el mismo día.
        self.crear_pago(
            "40.00",
            Pago.Metodo.EFECTIVO,
            Pago.Estado.REEMBOLSADO,
            self.fecha,
            self.fecha
        )

        # Venta realizada el día anterior y reembolsada hoy.
        self.crear_pago(
            "20.00",
            Pago.Metodo.QR,
            Pago.Estado.REEMBOLSADO,
            self.fecha_anterior,
            self.fecha
        )

        respuesta = self.client.post(
            "/api/pagos/conciliacion/",
            {
                "fecha": "2026-11-03",
                "efectivo_real": "0.00",
                "qr_real": "0.00",
            },
            format="json"
        )

        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)

        self.assertEqual(
            respuesta.data["ventas"]["efectivo"]["total"],
            "40.00"
        )

        self.assertEqual(
            respuesta.data["reembolsos"]["efectivo"]["total"],
            "40.00"
        )

        self.assertEqual(
            respuesta.data["ventas_netas"]["efectivo"],
            "0.00"
        )

        self.assertEqual(
            respuesta.data["ventas_netas"]["qr"],
            "-20.00"
        )

        self.assertFalse(respuesta.data["cuadra"])

    def test_detectar_diferencia_en_caja(self):

        self.crear_pago(
            "100.00",
            Pago.Metodo.EFECTIVO,
            Pago.Estado.COMPLETADO,
            self.fecha
        )

        respuesta = self.client.post(
            "/api/pagos/conciliacion/",
            {
                "fecha": "2026-11-03",
                "efectivo_real": "90.00",
                "qr_real": "0.00",
            },
            format="json"
        )

        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)

        self.assertEqual(
            respuesta.data["diferencias"]["efectivo"],
            "-10.00"
        )

        self.assertFalse(respuesta.data["cuadra"])

    def test_filtrar_ventas_por_fecha(self):

        self.crear_pago(
            "60.00",
            Pago.Metodo.EFECTIVO,
            Pago.Estado.COMPLETADO,
            self.fecha_anterior
        )

        respuesta = self.client.post(
            "/api/pagos/conciliacion/",
            {
                "fecha": "2026-11-03",
                "efectivo_real": "0.00",
                "qr_real": "0.00",
            },
            format="json"
        )

        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertEqual(respuesta.data["total_ventas"], "0.00")

    def test_rechazar_fecha_invalida(self):

        respuesta = self.client.post(
            "/api/pagos/conciliacion/",
            {
                "fecha": "fecha incorrecta",
                "efectivo_real": "0.00",
                "qr_real": "0.00",
            },
            format="json"
        )

        self.assertEqual(
            respuesta.status_code,
            status.HTTP_400_BAD_REQUEST
        )

    def test_rechazar_montos_negativos(self):

        respuesta = self.client.post(
            "/api/pagos/conciliacion/",
            {
                "fecha": "2026-11-03",
                "efectivo_real": "-10.00",
                "qr_real": "0.00",
            },
            format="json"
        )

        self.assertEqual(
            respuesta.status_code,
            status.HTTP_400_BAD_REQUEST
        )

    def test_mesero_no_puede_realizar_conciliacion(self):

        mesero = User.objects.create_user(
            username="mesero_conciliacion",
            password="Test12345",
            rol="mesero"
        )

        self.client.force_authenticate(user=mesero)

        respuesta = self.client.post(
            "/api/pagos/conciliacion/",
            {
                "fecha": "2026-11-03",
                "efectivo_real": "0.00",
                "qr_real": "0.00",
            },
            format="json"
        )

        self.assertEqual(
            respuesta.status_code,
            status.HTTP_403_FORBIDDEN
        )
