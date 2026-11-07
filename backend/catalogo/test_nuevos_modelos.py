from decimal import Decimal

from django.db import IntegrityError, transaction
from django.core.management import call_command
from django.test import TestCase

from .models import Categoria, ExistenciaProducto, Insumo, Producto, ProductoInsumo


class InventarioModelosTests(TestCase):
    def setUp(self):
        categoria = Categoria.objects.create(nombre="Bebidas")
        self.producto = Producto.objects.create(nombre="Café", precio="7.00", categoria=categoria, stock=8)
        self.insumo = Insumo.objects.create(nombre_insumo="Cápsula", unidad_medida="unidad", cantidad_stock=20)

    def test_producto_crea_una_existencia_y_guardar_stock_la_actualiza(self):
        self.assertEqual(self.producto.existencia.cantidad_stock, Decimal("8"))
        self.producto.stock = 5
        self.producto.save(update_fields=["stock"])
        self.assertEqual(ExistenciaProducto.objects.get(producto=self.producto).cantidad_stock, Decimal("5"))
        with self.assertRaises(IntegrityError), transaction.atomic():
            ExistenciaProducto.objects.create(producto=self.producto)

    def test_receta_no_admite_insumo_repetido_ni_cantidad_cero(self):
        ProductoInsumo.objects.create(producto=self.producto, insumo=self.insumo, cantidad_insumo_por_unidad=1)
        with self.assertRaises(IntegrityError), transaction.atomic():
            ProductoInsumo.objects.create(producto=self.producto, insumo=self.insumo, cantidad_insumo_por_unidad=1)
        otro = Insumo.objects.create(nombre_insumo="Azúcar", unidad_medida="sobre")
        with self.assertRaises(IntegrityError), transaction.atomic():
            ProductoInsumo.objects.create(producto=self.producto, insumo=otro, cantidad_insumo_por_unidad=0)

    def test_datos_demo_conservan_existencia_del_producto_existente(self):
        self.producto.stock = 5
        self.producto.save(update_fields=["stock"])
        call_command("seed_demo", verbosity=0)
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock, Decimal("5"))
