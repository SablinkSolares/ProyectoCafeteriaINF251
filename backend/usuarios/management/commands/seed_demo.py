"""Datos de demostración para probar las vistas de Carlos Quispe.

Uso:
    python manage.py seed_demo

Es idempotente: actualiza usuarios y productos, y solo crea pedidos si la
tabla está vacía. Las contraseñas son de prueba, nunca de producción.
"""
from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils import timezone

from catalogo.models import Categoria, Producto
from pedidos.models import DetallePedido, Pedido
from usuarios.models import Usuario

USUARIOS = [
    # usuario, contraseña, rol, staff, superusuario
    ("admin", "admin123", Usuario.Rol.ADMINISTRADOR, True, True),
    ("mesero", "mesero123", Usuario.Rol.MESERO, False, False),
    ("cajero", "cajero123", Usuario.Rol.CAJERO, False, False),
    ("cocina", "cocina123", Usuario.Rol.COCINA, False, False),
]

PRODUCTOS = [
    # nombre, categoría, precio, stock
    ("Té", "Bebidas", "5.00", 20),
    ("Café", "Bebidas", "7.00", 15),
    ("Cocoa", "Bebidas", "8.00", 4),
    ("Cocoa con leche", "Bebidas", "9.50", 0),
    ("Leche", "Bebidas", "6.00", 25),
    ("Pan", "Acompañamientos", "3.00", 30),
    ("Empanada", "Acompañamientos", "5.50", 12),
    ("Trozo de torta", "Acompañamientos", "12.00", 3),
    ("Trozo de rollo", "Acompañamientos", "10.00", 8),
    ("Sándwich de huevo", "Acompañamientos", "9.00", 2),
]

PEDIDOS = [
    # estado, minutos desde ahora, [(producto, cantidad)]
    (Pedido.Estado.ESPERA, 2, [("Café", 2), ("Pan", 1)]),
    (Pedido.Estado.ESPERA, 9, [("Cocoa", 1), ("Trozo de torta", 1)]),
    (Pedido.Estado.EN_PREPARACION, 14, [("Té", 1), ("Empanada", 2)]),
    (Pedido.Estado.LISTO, 21, [("Cocoa con leche", 1), ("Sándwich de huevo", 1)]),
    (Pedido.Estado.ENTREGADO, 35, [("Leche", 2), ("Trozo de rollo", 1)]),
]


class Command(BaseCommand):
    help = "Crea usuarios, categorías, productos y pedidos de demostración."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset-pedidos",
            action="store_true",
            help="Elimina los pedidos existentes y vuelve a crear los de demostración.",
        )

    def handle(self, *args, **options):
        self._crear_usuarios()
        self._crear_catalogo()
        if options["reset_pedidos"] and Pedido.objects.exists():
            Pedido.objects.all().delete()
            self.stdout.write("  Pedidos anteriores eliminados.")
        self._crear_pedidos()
        self.stdout.write(self.style.SUCCESS("Datos de demostración listos."))
        self.stdout.write("  admin/admin123 · mesero/mesero123 · cajero/cajero123 · cocina/cocina123")

    def _crear_usuarios(self):
        for username, password, rol, is_staff, is_superuser in USUARIOS:
            usuario, creado = Usuario.objects.get_or_create(username=username)
            usuario.rol = rol
            usuario.is_staff = is_staff
            usuario.is_superuser = is_superuser
            usuario.is_active = True
            usuario.set_password(password)
            usuario.save()
            estado = "creado" if creado else "actualizado"
            self.stdout.write(f"  Usuario {username} ({rol}) {estado}.")

    def _crear_catalogo(self):
        for nombre, categoria_nombre, precio, stock in PRODUCTOS:
            categoria, _ = Categoria.objects.get_or_create(nombre=categoria_nombre)
            Producto.objects.update_or_create(
                nombre=nombre,
                categoria=categoria,
                defaults={"precio": Decimal(precio), "stock": stock},
            )
        self.stdout.write(f"  {Categoria.objects.count()} categorías y {Producto.objects.count()} productos.")

    def _crear_pedidos(self):
        if Pedido.objects.exists():
            self.stdout.write("  Los pedidos ya existen; no se recrean.")
            return

        for estado, minutos, lineas in PEDIDOS:
            pedido = Pedido.objects.create(estado=estado)
            for nombre_producto, cantidad in lineas:
                producto = Producto.objects.get(nombre=nombre_producto)
                DetallePedido.objects.create(
                    pedido=pedido,
                    producto=producto,
                    cantidad=cantidad,
                    precio_unitario=producto.precio,
                )
            # auto_now_add no admite fechas manuales; se ajusta después de crear.
            creado_en = timezone.now() - timedelta(minutes=minutos)
            Pedido.objects.filter(pk=pedido.pk).update(creado_en=creado_en)
        self.stdout.write(f"  {Pedido.objects.count()} pedidos de ejemplo.")
