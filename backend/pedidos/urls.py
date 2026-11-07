
from rest_framework.routers import DefaultRouter

from .views import PedidoViewSet, PagoViewSet, WebhookQRView, NotificacionesView
from .reporting import ReportesView, DescargarReporteView
from django.urls import path

router = DefaultRouter(use_regex_path=False)

router.register("pedidos", PedidoViewSet, basename="pedidos")
router.register("pagos", PagoViewSet, basename="pagos")

urlpatterns = [
    path("notificaciones/", NotificacionesView.as_view(), name="notificaciones"),
    path("pagos/webhook-qr/", WebhookQRView.as_view(), name="webhook-qr"),
    path("reportes/", ReportesView.as_view(), name="reportes"),
    path("reportes/<int:pk>/pdf/", DescargarReporteView.as_view(), name="reporte-pdf"),
] + router.urls
