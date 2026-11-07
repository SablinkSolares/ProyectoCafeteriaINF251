"""Datos de demostración idempotentes; no reemplaza contraseñas ni inventario existente."""
import unicodedata
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from catalogo.models import Categoria, Producto, Insumo, ProductoInsumo
from pedidos.models import Pedido, Pago
from pedidos.serializers import PedidoCreateSerializer
from pedidos.insumos import descontar_insumos
from pedidos.services import confirmar_pago
from usuarios.models import Usuario

PRODUCTOS = [
    ("Té", "Bebidas", "5.00", 20), ("Café", "Bebidas", "7.00", 15),
    ("Cocoa", "Bebidas", "8.00", 4), ("Cocoa con leche", "Bebidas", "9.50", 0),
    ("Leche", "Bebidas", "6.00", 25), ("Pan", "Acompañamientos", "3.00", 30),
    ("Empanada", "Acompañamientos", "5.50", 12), ("Trozo de torta", "Acompañamientos", "12.00", 3),
    ("Trozo de rollo", "Acompañamientos", "10.00", 8), ("Sándwich de huevo", "Acompañamientos", "9.00", 2),
]

class Command(BaseCommand):
    help = "Crea datos demo sin sobrescribir cuentas, productos o existencias existentes."

    @transaction.atomic
    def handle(self, *args, **options):
        catalogo_nuevo = not Producto.objects.exists()
        usuarios = {}
        for nombre, rol in [("admin","administrador"),("mesero","mesero"),("cajero","cajero"),("cocina","cocina")]:
            usuario, nuevo = Usuario.objects.get_or_create(username=nombre, defaults={"rol":rol, "is_staff":nombre=="admin", "is_superuser":nombre=="admin"})
            if nuevo:
                usuario.set_password(nombre+"123")
                usuario.save()
            usuarios[nombre] = usuario
        ingredientes = {}
        for nombre, unidad, cantidad in [("Café molido","g",500),("Té en hojas","g",100),("Cocoa en polvo","g",400),("Leche fresca","ml",3000)]:
            ingredientes[nombre], _ = Insumo.objects.get_or_create(nombre_insumo=nombre, defaults={"unidad_medida":unidad,"cantidad_stock":cantidad})
        recetas = {"Café":[("Café molido","10")], "Té":[("Té en hojas","2")], "Cocoa":[("Cocoa en polvo","20")], "Cocoa con leche":[("Cocoa en polvo","20"),("Leche fresca","200")], "Leche":[("Leche fresca","200")]}
        productos = {}
        for nombre, cat, precio, stock in PRODUCTOS:
            slug = unicodedata.normalize("NFKD",nombre).encode("ascii","ignore").decode().lower().replace(" ","-")
            categoria, _ = Categoria.objects.get_or_create(nombre=cat, defaults={"imagen_carrusel":"/images/carrusel/"+("bebidas" if cat=="Bebidas" else "acompanamientos")+".jpg"})
            producto, nuevo = Producto.objects.get_or_create(nombre=nombre, categoria=categoria, defaults={"precio":Decimal(precio),"stock":stock,"imagen":f"/images/productos/{slug}.jpg","preparable":nombre in recetas})
            if not producto.imagen:
                producto.imagen = f"/images/productos/{slug}.jpg"
                producto.save(update_fields=["imagen"])
            if nuevo and producto.preparable:
                for insumo, cantidad in recetas[nombre]:
                    ProductoInsumo.objects.create(producto=producto, insumo=ingredientes[insumo], cantidad_insumo_por_unidad=cantidad)
            productos[nombre] = producto
        if catalogo_nuevo and not Pedido.objects.exists():
            for indice, (estado, lineas) in enumerate([
                ("ESPERA",[("Café",2),("Pan",1)]),
                ("EN_PREPARACION",[("Té",1),("Empanada",2)]),
                ("LISTO",[("Cocoa",1),("Trozo de torta",1)]),
                ("ENTREGADO",[("Leche",1),("Trozo de rollo",1)]),
                ("ENTREGADO",[("Café",1)]),
            ]):
                serializer = PedidoCreateSerializer(data={"mesa":indice+1,"detalles":[{"producto":productos[n].pk,"cantidad":c} for n,c in lineas]})
                serializer.is_valid(raise_exception=True)
                p = serializer.save(registrado_por=usuarios["mesero"])
                if estado != "ESPERA":
                    descontar_insumos(p)
                    p.preparado_por = usuarios["cocina"]
                    p.en_preparacion_en = timezone.now()
                if estado in {"LISTO","ENTREGADO"}:
                    p.listo_por = usuarios["cocina"]
                    p.listo_en = timezone.now()
                if estado == "ENTREGADO":
                    p.entregado_por = usuarios["mesero"]
                    p.entregado_en = timezone.now()
                p.estado = estado
                p.save()
                if indice == 4:
                    pago = Pago.objects.create(pedido=p,monto=p.total,monto_recibido=10,metodo="EFECTIVO",creado_por=usuarios["cajero"])
                    confirmar_pago(pago,usuarios["cajero"])
        self.stdout.write(self.style.SUCCESS("Datos demo listos. Cuentas nuevas: admin/admin123, mesero/mesero123, cajero/cajero123, cocina/cocina123."))
