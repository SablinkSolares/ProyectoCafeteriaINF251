from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from dinocafe.permissions import EsAdministrador

from .models import Pedido
from .serializers import PedidoCreateSerializer, PedidoSerializer

# Máquina de estados de RF5: estado actual -> (siguiente estado, roles autorizados).
TRANSICIONES = {
    Pedido.Estado.ESPERA: (Pedido.Estado.EN_PREPARACION, {"administrador", "cocina"}),
    Pedido.Estado.EN_PREPARACION: (Pedido.Estado.LISTO, {"administrador", "cocina"}),
    Pedido.Estado.LISTO: (Pedido.Estado.ENTREGADO, {"administrador", "mesero"}),
}


class PedidoViewSet(viewsets.ModelViewSet):
    """Listado para cocina, registro de pedidos y cambio de estado."""

    permission_classes = [IsAuthenticated]
    serializer_class = PedidoSerializer

    def get_permissions(self):
        if self.action in {"update", "partial_update", "destroy"}:
            return [EsAdministrador()]
        return [IsAuthenticated()]

    def get_queryset(self):
        qs = Pedido.objects.prefetch_related("detalles__producto")
        estados = self.request.query_params.get("estado", "").strip()
        if estados:
            # El frontend envía ?estado=ESPERA,EN_PREPARACION,LISTO
            lista = [e.strip() for e in estados.split(",") if e.strip()]
            qs = qs.filter(estado__in=lista)
        return qs

    def get_serializer_class(self):
        if self.action == "create":
            return PedidoCreateSerializer
        return PedidoSerializer

    def create(self, request, *args, **kwargs):
        if request.user.rol not in {"administrador", "mesero"}:
            raise PermissionDenied("Solo el mesero o el administrador registran pedidos.")
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        pedido = serializer.save()
        return Response(
            PedidoSerializer(pedido, context=self.get_serializer_context()).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["patch"], url_path="estado")
    def cambiar_estado(self, request, pk=None):
        pedido = self.get_object()
        nuevo = request.data.get("estado")

        if nuevo not in Pedido.Estado.values:
            raise ValidationError(
                {"estado": "Estado no válido. Usa ESPERA, EN_PREPARACION, LISTO o ENTREGADO."}
            )

        transicion = TRANSICIONES.get(pedido.estado)
        if not transicion:
            raise ValidationError({"estado": "El pedido ya fue entregado; no admite más cambios."})

        siguiente, roles = transicion
        if request.user.rol not in roles:
            raise PermissionDenied(
                f"El rol {request.user.rol} no puede cambiar de {pedido.estado} a {nuevo}."
            )
        if nuevo != siguiente:
            raise ValidationError(
                {"estado": f"Transición inválida: {pedido.estado} → {nuevo}. Debe ser {siguiente}."}
            )

        pedido.estado = nuevo
        pedido.save(update_fields=["estado", "actualizado_en"])
        return Response(PedidoSerializer(pedido, context=self.get_serializer_context()).data)
