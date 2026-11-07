from time import perf_counter
from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from catalogo.models import Categoria, Producto


class RegistroRendimientoTests(TestCase):
    def test_registrar_y_calcular_total_en_menos_de_cinco_segundos(self):
        usuario=get_user_model().objects.create(username="rendimiento",rol="mesero")
        categoria=Categoria.objects.create(nombre="Rendimiento")
        productos=[Producto.objects.create(nombre=f"Producto {i}",categoria=categoria,precio="7.35",stock=100) for i in range(10)]
        cliente=APIClient(); cliente.force_authenticate(usuario)
        tiempos=[]
        for _ in range(10):
            inicio=perf_counter()
            respuesta=cliente.post("/api/pedidos/",{"mesa":1,"detalles":[{"producto":p.pk,"cantidad":2} for p in productos]},format="json")
            tiempos.append(perf_counter()-inicio)
            self.assertEqual(respuesta.status_code,201,respuesta.data)
            self.assertEqual(Decimal(respuesta.data["total"]),Decimal("147.00"))
        self.assertLess(max(tiempos),5)
        print(f"RNF2: 10 registros de 10 productos: promedio {sum(tiempos)/len(tiempos)*1000:.1f} ms; máximo {max(tiempos)*1000:.1f} ms (cliente Django, sin red).")
