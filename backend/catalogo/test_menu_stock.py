from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from .models import Categoria, Producto, Insumo, ProductoInsumo


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class MenuYStockTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.usuarios = {rol: get_user_model().objects.create_user(username=rol, password="prueba123", rol=rol) for rol in ["administrador", "mesero", "cajero", "cocina"]}
        cls.categoria = Categoria.objects.create(nombre="Acompañamientos")
        cls.producto = Producto.objects.create(nombre="Pan", categoria=cls.categoria, precio="3.50", stock=10, imagen="/images/productos/pan.jpg")
        cls.inactivo = Producto.objects.create(nombre="Retirado", categoria=cls.categoria, precio="9.00", stock=20, activo=False)
        cls.preparable = Producto.objects.create(nombre="Bebida preparada", categoria=cls.categoria, precio="7.00", preparable=True)
        cls.insumo = Insumo.objects.create(nombre_insumo="Ingrediente", unidad_medida="g", cantidad_stock=100)
        ProductoInsumo.objects.create(producto=cls.preparable, insumo=cls.insumo, cantidad_insumo_por_unidad=10)

    def setUp(self):
        self.client = APIClient()

    def test_menu_sin_sesion_muestra_solo_productos_activos_y_datos_publicos(self):
        respuesta = self.client.get("/api/menu/?activo=false")
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual({p["id"] for p in respuesta.data["productos"]}, {self.producto.pk, self.preparable.pk})
        for producto in respuesta.data["productos"]:
            self.assertEqual(set(producto), {"id", "nombre", "categoria", "categoria_nombre", "precio", "imagen"})
        self.assertEqual(respuesta.data["categorias"], [{"id": self.categoria.pk, "nombre": self.categoria.nombre}])

    def test_menu_publico_no_se_bloquea_por_token_vencido_ni_permite_escribir(self):
        self.client.credentials(HTTP_AUTHORIZATION="Bearer token-no-valido")
        self.assertEqual(self.client.get("/api/menu/").status_code, 200)
        self.assertEqual(self.client.post("/api/menu/", {}, format="json").status_code, 405)

    def test_menu_no_abre_catalogo_operaciones_ni_usuarios_al_publico(self):
        for ruta in ["/api/productos/", "/api/insumos/", "/api/pedidos/", "/api/usuarios/"]:
            self.assertEqual(self.client.get(ruta).status_code, 401, ruta)

    def test_solo_administrador_puede_actualizar_stock(self):
        url = f"/api/productos/{self.producto.pk}/stock/"
        self.assertEqual(self.client.patch(url, {"stock": 50}, format="json").status_code, 401)
        for rol in ["mesero", "cajero", "cocina"]:
            self.client.force_authenticate(self.usuarios[rol])
            self.assertEqual(self.client.patch(url, {"stock": 50}, format="json").status_code, 403)
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock, 10)

    def test_actualizar_stock_no_modifica_precio_y_admite_cero(self):
        self.client.force_authenticate(self.usuarios["administrador"])
        respuesta = self.client.patch(f"/api/productos/{self.producto.pk}/stock/", {"stock": 0, "stock_anterior": 10, "precio": "0.01"}, format="json")
        self.assertEqual(respuesta.status_code, 200, respuesta.data)
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock, 0)
        self.assertEqual(str(self.producto.precio), "3.50")

    def test_rechaza_stock_negativo_fraccionario_o_fuera_de_limite(self):
        self.client.force_authenticate(self.usuarios["administrador"])
        for valor in [-1, "2.5", "NaN", 1000000000]:
            self.assertEqual(self.client.patch(f"/api/productos/{self.producto.pk}/stock/", {"stock": valor}, format="json").status_code, 400)
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock, 10)

    def test_no_sobrescribe_stock_que_cambio_mientras_se_editaba(self):
        self.client.force_authenticate(self.usuarios["administrador"])
        self.producto.stock = 8
        self.producto.save(update_fields=["stock"])
        respuesta = self.client.patch(f"/api/productos/{self.producto.pk}/stock/", {"stock": 20, "stock_anterior": 10}, format="json")
        self.assertEqual(respuesta.status_code, 409)
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock, 8)

    def test_preparables_se_actualizan_por_insumos(self):
        self.client.force_authenticate(self.usuarios["administrador"])
        respuesta = self.client.patch(f"/api/productos/{self.preparable.pk}/stock/", {"stock": 99}, format="json")
        self.assertEqual(respuesta.status_code, 400)
        self.assertEqual(self.preparable.stock_disponible, 10)
