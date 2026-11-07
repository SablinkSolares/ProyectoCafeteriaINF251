
from decimal import Decimal

from django.contrib.auth import get_user_model

from rest_framework.test import APITestCase
from rest_framework import status

from .models import Categoria, Producto


User = get_user_model()


class ProductoBusquedaTests(APITestCase):

    def setUp(self):

        self.admin = User.objects.create_user(
            username="admin_catalogo",
            password="Test12345",
            rol="administrador"
        )

        self.usuario = User.objects.create_user(
            username="usuario_catalogo",
            password="Test12345",
            rol="mesero"
        )

        self.categoria_bebidas = Categoria.objects.create(
            nombre="Bebidas"
        )

        self.categoria_comidas = Categoria.objects.create(
            nombre="Comidas"
        )

        self.cafe = Producto.objects.create(
            nombre="Café Americano",
            categoria=self.categoria_bebidas,
            precio=Decimal("15.00"),
            stock=20
        )

        self.capuchino = Producto.objects.create(
            nombre="Capuchino",
            categoria=self.categoria_bebidas,
            precio=Decimal("25.00"),
            stock=10
        )

        self.sandwich = Producto.objects.create(
            nombre="Sándwich de pollo",
            categoria=self.categoria_comidas,
            precio=Decimal("30.00"),
            stock=0
        )

        self.client.force_authenticate(user=self.usuario)

    def test_buscar_producto_por_nombre(self):

        respuesta = self.client.get(
            "/api/productos/?q=Americano"
        )

        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertEqual(respuesta.data["count"], 1)
        self.assertEqual(
            respuesta.data["results"][0]["nombre"],
            "Café Americano"
        )

    def test_busqueda_sin_distinguir_mayusculas(self):

        respuesta = self.client.get(
        "/api/productos/?q=AMERICANO"
        )

        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertEqual(respuesta.data["count"], 1)

    def test_busqueda_parcial(self):

        respuesta = self.client.get(
            "/api/productos/?q=Cap"
        )

        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertEqual(respuesta.data["count"], 1)

    def test_busqueda_sin_resultados(self):

        respuesta = self.client.get(
            "/api/productos/?q=Pizza"
        )

        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertEqual(respuesta.data["count"], 0)

    def test_filtrar_por_categoria(self):

        respuesta = self.client.get(
            f"/api/productos/?categoria={self.categoria_bebidas.id}"
        )

        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertEqual(respuesta.data["count"], 2)

    def test_filtrar_por_precio_minimo(self):

        respuesta = self.client.get(
            "/api/productos/?precio_min=20"
        )

        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertEqual(respuesta.data["count"], 2)

    def test_filtrar_por_precio_maximo(self):

        respuesta = self.client.get(
            "/api/productos/?precio_max=20"
        )

        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertEqual(respuesta.data["count"], 1)

    def test_filtrar_por_disponibilidad(self):

        respuesta = self.client.get(
            "/api/productos/?disponible=true"
        )

        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertEqual(respuesta.data["count"], 2)

    def test_filtrar_productos_agotados(self):

        respuesta = self.client.get(
            "/api/productos/?disponible=false"
        )

        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertEqual(respuesta.data["count"], 1)

    def test_combinar_filtros(self):

        respuesta = self.client.get(
            f"/api/productos/?q=Americano"
            f"&categoria={self.categoria_bebidas.id}"
            "&precio_min=10&precio_max=20&disponible=true"
        )

        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertEqual(respuesta.data["count"], 1)

    def test_ordenar_por_precio(self):

        respuesta = self.client.get(
            "/api/productos/?ordering=-precio"
        )

        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)

        productos = respuesta.data["results"]

        self.assertEqual(
            productos[0]["nombre"],
            "Sándwich de pollo"
        )

    def test_paginacion(self):

        respuesta = self.client.get(
            "/api/productos/?page=1&page_size=2"
        )

        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertEqual(len(respuesta.data["results"]), 2)
        self.assertEqual(respuesta.data["count"], 3)

    def test_rechazar_categoria_invalida(self):

        respuesta = self.client.get(
            "/api/productos/?categoria=abc"
        )

        self.assertEqual(
            respuesta.status_code,
            status.HTTP_400_BAD_REQUEST
        )

    def test_rechazar_precio_invalido(self):

        respuesta = self.client.get(
            "/api/productos/?precio_min=abc"
        )

        self.assertEqual(
            respuesta.status_code,
            status.HTTP_400_BAD_REQUEST
        )

    def test_rechazar_rango_de_precio_incorrecto(self):

        respuesta = self.client.get(
            "/api/productos/?precio_min=50&precio_max=10"
        )

        self.assertEqual(
            respuesta.status_code,
            status.HTTP_400_BAD_REQUEST
        )

    def test_rechazar_disponibilidad_invalida(self):

        respuesta = self.client.get(
            "/api/productos/?disponible=si"
        )

        self.assertEqual(
            respuesta.status_code,
            status.HTTP_400_BAD_REQUEST
        )

    def test_rechazar_ordenamiento_invalido(self):

        respuesta = self.client.get(
            "/api/productos/?ordering=categoria"
        )

        self.assertEqual(
            respuesta.status_code,
            status.HTTP_400_BAD_REQUEST
        )

    def test_usuario_no_autenticado(self):

        self.client.force_authenticate(user=None)

        respuesta = self.client.get("/api/productos/")

        self.assertEqual(
            respuesta.status_code,
            status.HTTP_401_UNAUTHORIZED
        )

    def test_mesero_no_puede_crear_producto(self):

        respuesta = self.client.post(
            "/api/productos/",
            {
                "nombre": "Té",
                "categoria": self.categoria_bebidas.id,
                "precio": "10.00",
                "stock": 5
            },
            format="json"
        )

        self.assertEqual(
            respuesta.status_code,
            status.HTTP_403_FORBIDDEN
        )

    def test_administrador_puede_crear_producto(self):

        self.client.force_authenticate(user=self.admin)

        respuesta = self.client.post(
            "/api/productos/",
            {
                "nombre": "Té verde",
                "imagen": "/images/productos/te.jpg",
                "categoria": self.categoria_bebidas.id,
                "precio": "12.00",
                "stock": 5
            },
            format="json"
        )

        self.assertEqual(
            respuesta.status_code,
            status.HTTP_201_CREATED
        )
