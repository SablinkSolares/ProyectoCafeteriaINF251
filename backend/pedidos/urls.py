
from rest_framework.routers import DefaultRouter

from .views import PedidoViewSet, PagoViewSet

router = DefaultRouter()

router.register("pedidos", PedidoViewSet, basename="pedidos")
router.register("pagos", PagoViewSet, basename="pagos")

urlpatterns = router.urls
