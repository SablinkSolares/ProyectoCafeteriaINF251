
from django.contrib.auth import get_user_model
from django.urls import reverse

from rest_framework.test import APITestCase, APIRequestFactory
from rest_framework import status
from rest_framework_simplejwt.tokens import AccessToken

from dinocafe.permissions import EsAdministrador

Usuario = get_user_model()


class AutenticacionJWTTests(APITestCase):

    def setUp(self):
        self.usuario = Usuario.objects.create_user(
            username="mesero_test",
            password="ClaveSegura123",
            rol="mesero",
        )

        self.admin = Usuario.objects.create_user(
            username="admin_test",
            password="ClaveSegura123",
            rol="administrador",
        )

    def test_login_correcto_devuelve_tokens_y_rol(self):
        response = self.client.post(
            reverse("login"),
            {
                "username": "mesero_test",
                "password": "ClaveSegura123",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
        self.assertEqual(response.data["rol"], "mesero")
        self.assertEqual(response.data["username"], "mesero_test")

    def test_token_access_contiene_rol_y_username(self):
        response = self.client.post(
            reverse("login"),
            {
                "username": "mesero_test",
                "password": "ClaveSegura123",
            },
            format="json",
        )

        token = AccessToken(response.data["access"])

        self.assertEqual(token["rol"], "mesero")
        self.assertEqual(token["username"], "mesero_test")

    def test_login_con_password_incorrecta_es_rechazado(self):
        response = self.client.post(
            reverse("login"),
            {
                "username": "mesero_test",
                "password": "incorrecta",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_login_con_usuario_inexistente_es_rechazado(self):
        response = self.client.post(
            reverse("login"),
            {
                "username": "usuario_inexistente",
                "password": "ClaveSegura123",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_refresh_devuelve_nuevo_access_token(self):
        login = self.client.post(
            reverse("login"),
            {
                "username": "mesero_test",
                "password": "ClaveSegura123",
            },
            format="json",
        )

        response = self.client.post(
            reverse("token_refresh"),
            {"refresh": login.data["refresh"]},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)

    def test_usuario_tiene_rol_por_defecto_mesero(self):
        usuario = Usuario.objects.create_user(
            username="nuevo_usuario",
            password="ClaveSegura123",
        )

        self.assertEqual(usuario.rol, Usuario.Rol.MESERO)


class PermisosAdministradorTests(APITestCase):

    def setUp(self):
        self.factory = APIRequestFactory()
        self.permiso = EsAdministrador()

    def comprobar_permiso(self, usuario):
        request = self.factory.get("/")
        request.user = usuario
        return self.permiso.has_permission(request, None)

    def test_administrador_tiene_permiso(self):
        admin = Usuario.objects.create_user(
            username="admin",
            password="ClaveSegura123",
            rol="administrador",
        )

        self.assertTrue(self.comprobar_permiso(admin))

    def test_mesero_no_tiene_permiso(self):
        mesero = Usuario.objects.create_user(
            username="mesero",
            password="ClaveSegura123",
            rol="mesero",
        )

        self.assertFalse(self.comprobar_permiso(mesero))

    def test_cajero_no_tiene_permiso(self):
        cajero = Usuario.objects.create_user(
            username="cajero",
            password="ClaveSegura123",
            rol="cajero",
        )

        self.assertFalse(self.comprobar_permiso(cajero))

    def test_cocina_no_tiene_permiso(self):
        cocina = Usuario.objects.create_user(
            username="cocina",
            password="ClaveSegura123",
            rol="cocina",
        )

        self.assertFalse(self.comprobar_permiso(cocina))

    def test_usuario_no_autenticado_no_tiene_permiso(self):
        from django.contrib.auth.models import AnonymousUser

        self.assertFalse(self.comprobar_permiso(AnonymousUser()))
