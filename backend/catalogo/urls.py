from rest_framework.routers import DefaultRouter

from .views import CategoriaViewSet, ProductoViewSet, InsumoViewSet, SubirImagenView, ConfiguracionPagoView, MenuPublicoView
from django.urls import path

router = DefaultRouter(use_regex_path=False)
router.register("categorias", CategoriaViewSet, basename="categorias")
router.register("productos", ProductoViewSet, basename="productos")
router.register("insumos", InsumoViewSet, basename="insumos")

urlpatterns = [path("menu/", MenuPublicoView.as_view(), name="menu-publico"), path("imagenes/", SubirImagenView.as_view()), path("configuracion-pago/", ConfiguracionPagoView.as_view())] + router.urls
