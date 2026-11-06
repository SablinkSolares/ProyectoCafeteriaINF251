from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase


Usuario = get_user_model()


class CrearCuentasTests(APITestCase):
    def setUp(self):
        self.admin = Usuario.objects.create_user(username="admin_test_cuentas", password="ClavePrueba1", rol="administrador")
        self.datos = {"username": "empleado_nuevo", "password": "ClavePrueba2", "rol": "mesero", "first_name": "Ana"}

    def test_admin_crea_cuenta_con_hash_y_puede_iniciar_sesion(self):
        self.client.force_authenticate(self.admin)
        respuesta = self.client.post("/api/usuarios/", self.datos, format="json")
        self.assertEqual(respuesta.status_code, 201, respuesta.data)
        self.assertNotIn("password", respuesta.data)
        usuario = Usuario.objects.get(username="empleado_nuevo")
        self.assertTrue(usuario.check_password("ClavePrueba2"))
        self.assertNotEqual(usuario.password, "ClavePrueba2")
        self.assertFalse(usuario.is_superuser)
        self.assertFalse(usuario.is_staff)
        self.client.force_authenticate(user=None)
        login = self.client.post("/api/auth/login/", {"username": usuario.username, "password": "ClavePrueba2"}, format="json")
        self.assertEqual(login.status_code, 200)
        self.assertEqual(login.data["rol"], "mesero")

    def test_no_administradores_no_pueden_crear_ni_listar(self):
        self.assertEqual(self.client.get("/api/usuarios/").status_code, 401)
        for rol in ["mesero", "cajero", "cocina"]:
            usuario = Usuario.objects.create_user(username=f"rol_{rol}", password="ClavePrueba1", rol=rol)
            self.client.force_authenticate(usuario)
            self.assertEqual(self.client.get("/api/usuarios/").status_code, 403)
            self.assertEqual(self.client.post("/api/usuarios/", self.datos, format="json").status_code, 403)
        self.assertFalse(Usuario.objects.filter(username="empleado_nuevo").exists())

    def test_no_se_pueden_asignar_privilegios_de_django_por_entrada(self):
        self.client.force_authenticate(self.admin)
        respuesta = self.client.post("/api/usuarios/", {**self.datos, "rol": "administrador", "is_staff": True, "is_superuser": True}, format="json")
        self.assertEqual(respuesta.status_code, 201, respuesta.data)
        usuario = Usuario.objects.get(username="empleado_nuevo")
        self.assertEqual(usuario.rol, "administrador")
        self.assertFalse(usuario.is_staff)
        self.assertFalse(usuario.is_superuser)

    def test_valida_nombre_contrasena_rol_y_duplicados(self):
        self.client.force_authenticate(self.admin)
        for datos in [
            {**self.datos, "username": ""},
            {**self.datos, "username": "nombre con espacios"},
            {**self.datos, "password": "corta"},
            {**self.datos, "rol": "inexistente"},
            {k: v for k, v in self.datos.items() if k != "rol"},
        ]:
            self.assertEqual(self.client.post("/api/usuarios/", datos, format="json").status_code, 400)
        self.assertEqual(self.client.post("/api/usuarios/", self.datos, format="json").status_code, 201)
        self.assertEqual(self.client.post("/api/usuarios/", self.datos, format="json").status_code, 400)

    def test_lista_no_expone_contrasenas_y_solo_permite_consulta_y_creacion(self):
        self.client.force_authenticate(self.admin)
        respuesta = self.client.get("/api/usuarios/")
        self.assertEqual(respuesta.status_code, 200)
        self.assertTrue(any(u["username"] == self.admin.username for u in respuesta.data))
        self.assertTrue(all("password" not in u for u in respuesta.data))
        self.assertEqual(self.client.delete("/api/usuarios/").status_code, 405)
