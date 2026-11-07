from django.contrib import admin
from django.urls import include, path

from .views import health
from usuarios.views import CuentaListCreateView
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),
    path("health/", health, name="health-root"),
    path("api/health/", health, name="health"),
    path("api/auth/", include("usuarios.urls")),
    path("api/usuarios/", CuentaListCreateView.as_view(), name="cuentas"),
    path("api/", include("catalogo.urls")),
    path("api/", include("pedidos.urls")),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
