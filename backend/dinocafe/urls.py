from django.contrib import admin
from django.urls import include, path

from .views import health
from usuarios.views import CuentaListCreateView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("health/", health, name="health-root"),
    path("api/health/", health, name="health"),
    path("api/auth/", include("usuarios.urls")),
    path("api/usuarios/", CuentaListCreateView.as_view(), name="cuentas"),
    path("api/", include("catalogo.urls")),
    path("api/", include("pedidos.urls")),
]
