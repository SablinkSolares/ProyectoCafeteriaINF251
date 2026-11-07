from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest import skipUnless
from django.db import connection, connections
from django.test import TransactionTestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from catalogo.models import Categoria, Producto, Insumo, ProductoInsumo
from .models import ReservaInsumo


@skipUnless(connection.vendor == "postgresql", "La concurrencia de reservas requiere PostgreSQL y bloqueos de fila.")
class ConcurrenciaPostgresTests(TransactionTestCase):
    def test_dos_productos_comparten_ultimo_insumo(self):
        usuario=get_user_model().objects.create(username="mesero-concurrente",rol="mesero")
        categoria=Categoria.objects.create(nombre="Prueba concurrente")
        insumo=Insumo.objects.create(nombre_insumo="Última porción",unidad_medida="unidad",cantidad_stock=1)
        productos=[]
        for n in range(2):
            p=Producto.objects.create(nombre=f"Preparación {n}",categoria=categoria,precio=7,preparable=True,imagen="/images/productos/cafe.jpg")
            ProductoInsumo.objects.create(producto=p,insumo=insumo,cantidad_insumo_por_unidad=1)
            productos.append(p.pk)
        barrera=Barrier(2)
        def pedir(pk):
            cliente=APIClient(); cliente.force_authenticate(usuario)
            try:
                barrera.wait(timeout=10)
                return cliente.post("/api/pedidos/",{"mesa":1,"detalles":[{"producto":pk,"cantidad":1}]},format="json").status_code
            finally:
                connections.close_all()
        with ThreadPoolExecutor(max_workers=2) as pool:
            resultados=list(pool.map(pedir,productos))
        self.assertEqual(sorted(resultados),[201,400])
        self.assertEqual(ReservaInsumo.objects.filter(estado="RESERVADA").count(),1)
