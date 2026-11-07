import hashlib
import hmac
import json
from django.conf import settings
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from dinocafe.permissions import EsAdministrador
from .models import Pedido, Pago, Notificacion
from .serializers import PedidoCreateSerializer, PedidoSerializer, PagoSerializer
from .services import confirmar_pago, cancelar_pedido, reembolsar_pago, notificar
from .insumos import descontar_insumos
from catalogo.models import ConfiguracionPago
from decimal import Decimal


def exigir_rol(request, roles):
    if request.user.rol not in roles:
        raise PermissionDenied("Tu rol no tiene permiso para esta operación.")


TRANSICIONES = {
    "ESPERA": ("EN_PREPARACION", {"administrador", "cocina"}, "preparado_por", "en_preparacion_en"),
    "EN_PREPARACION": ("LISTO", {"administrador", "cocina"}, "listo_por", "listo_en"),
    "LISTO": ("ENTREGADO", {"administrador", "mesero"}, "entregado_por", "entregado_en"),
}


class PedidoViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = PedidoSerializer
    lookup_value_converter = "int"
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self):
        qs = Pedido.objects.select_related("pago", "registrado_por", "preparado_por", "listo_por", "entregado_por").prefetch_related("detalles__producto__existencia", "detalles__producto__insumos__insumo", "reemplazos")
        rol = self.request.user.rol
        if rol in {"cocina", "mesero"}:
            qs = qs.filter(estado__in=["ESPERA", "EN_PREPARACION", "LISTO"])
        estados = self.request.query_params.get("estado", "")
        if estados:
            lista = estados.split(",")
            if any(e not in Pedido.Estado.values for e in lista):
                raise ValidationError({"estado": "Filtro de estado inválido."})
            qs = qs.filter(estado__in=lista)
        fecha = self.request.query_params.get("fecha")
        if fecha:
            try:
                dia = parse_date(fecha)
            except ValueError:
                dia = None
            if not dia:
                raise ValidationError({"fecha": "Usa una fecha válida AAAA-MM-DD."})
            qs = qs.filter(creado_en__date=dia)
        return qs

    def create(self, request, *args, **kwargs):
        exigir_rol(request, {"administrador", "cajero", "mesero"})
        serializer = PedidoCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        pedido = serializer.save(registrado_por=request.user)
        return Response(PedidoSerializer(pedido, context={"request": request}).data, status=status.HTTP_201_CREATED)

    def partial_update(self, request, *args, **kwargs):
        raise ValidationError({"pedido": "Usa las acciones de estado, cancelación o cambio de pedido."})

    @transaction.atomic
    @action(detail=True, methods=["patch"], url_path="estado")
    def cambiar_estado(self, request, pk=None):
        pedido = get_object_or_404(self.get_queryset().select_for_update(of=("self",)), pk=pk)
        transicion = TRANSICIONES.get(pedido.estado)
        if not transicion:
            raise ValidationError({"estado": "El pedido no admite esta transición."})
        siguiente, roles, responsable, fecha = transicion
        exigir_rol(request, roles)
        if request.data.get("estado") != siguiente:
            raise ValidationError({"estado": f"El siguiente estado debe ser {siguiente}."})
        if siguiente == "EN_PREPARACION":
            descontar_insumos(pedido)
        pedido.estado = siguiente
        setattr(pedido, responsable, request.user)
        setattr(pedido, fecha, timezone.now())
        pedido.save(update_fields=["estado", responsable, fecha, "actualizado_en"])
        if siguiente == "LISTO":
            notificar(pedido, "PEDIDO_LISTO", f"Pedido #{pedido.pk}, mesa {pedido.mesa}, listo para entregar.")
        return Response(PedidoSerializer(pedido, context={"request": request}).data)

    @transaction.atomic
    @action(detail=True, methods=["post"], url_path="cancelar")
    def cancelar(self, request, pk=None):
        exigir_rol(request, {"administrador", "cajero", "mesero"})
        motivo = str(request.data.get("motivo", "")).strip()
        if not motivo or len(motivo) > 500:
            raise ValidationError({"motivo": "Indica un motivo de hasta 500 caracteres."})
        pedido = get_object_or_404(Pedido.objects.select_for_update(), pk=pk)
        cancelar_pedido(pedido, motivo)
        return Response(PedidoSerializer(pedido, context={"request": request}).data)

    @transaction.atomic
    @action(detail=True, methods=["post"], url_path="cambiar")
    def cambiar(self, request, pk=None):
        exigir_rol(request, {"administrador", "cajero"})
        motivo = str(request.data.get("motivo", "")).strip()
        if not motivo or len(motivo) > 500:
            raise ValidationError({"motivo": "Indica el motivo del cambio (hasta 500 caracteres)."})
        original = get_object_or_404(Pedido.objects.select_for_update(), pk=pk)
        if original.reemplazos.exists():
            raise ValidationError({"pedido": "El pedido ya fue reemplazado."})
        if original.estado == "CANCELADO":
            raise ValidationError({"pedido": "El pedido ya está cancelado."})
        pago = Pago.objects.select_for_update().filter(pedido=original).first()
        if original.estado == "ENTREGADO" and (not pago or pago.estado != "COMPLETADO"):
            raise ValidationError({"pedido": "Para cambiar un pedido entregado, registra primero su pago y luego el cambio con reembolso."})
        if pago and pago.estado == "COMPLETADO":
            reembolsar_pago(pago, motivo, request.user)
        if original.estado != "ENTREGADO":
            cancelar_pedido(original, motivo)
        serializer = PedidoCreateSerializer(data={"mesa": request.data.get("mesa", original.mesa), "observaciones": request.data.get("observaciones", original.observaciones), "detalles": request.data.get("detalles", [])})
        serializer.is_valid(raise_exception=True)
        nuevo = serializer.save(registrado_por=request.user, pedido_original=original, motivo_cambio=motivo)
        return Response(PedidoSerializer(nuevo, context={"request": request}).data, status=201)


class PagoViewSet(viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = PagoSerializer
    lookup_value_converter = "int"
    queryset = Pago.objects.select_related("pedido", "reembolso", "creado_por", "verificado_por")

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        exigir_rol(request, {"administrador", "cajero"})

    def list(self, request):
        return Response(self.get_serializer(self.get_queryset(), many=True).data)

    def retrieve(self, request, pk=None):
        return Response(self.get_serializer(self.get_object()).data)

    @transaction.atomic
    def create(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if serializer.validated_data["metodo"] == "QR":
            config, _ = ConfiguracionPago.objects.get_or_create(pk=1)
            if not config.qr_habilitado:
                raise ValidationError({"metodo": "Los pagos QR están deshabilitados."})
        pedido = get_object_or_404(Pedido.objects.select_for_update(), pk=serializer.validated_data["pedido"].pk)
        if pedido.estado != "ENTREGADO" or Pago.objects.filter(pedido=pedido).exists():
            raise ValidationError({"pedido": "El pedido debe estar entregado y no tener un pago registrado."})
        pago = serializer.save(creado_por=request.user)
        if pago.metodo == "EFECTIVO":
            confirmar_pago(pago, request.user)
        return Response(self.get_serializer(pago).data, status=201)

    @transaction.atomic
    @action(detail=True, methods=["post"], url_path="confirmar")
    def confirmar(self, request, pk=None):
        inicial = get_object_or_404(Pago, pk=pk)
        pedido = get_object_or_404(Pedido.objects.select_for_update(), pk=inicial.pedido_id)
        pago = get_object_or_404(Pago.objects.select_for_update(), pk=pk)
        pago.pedido = pedido
        confirmar_pago(pago, request.user)
        return Response(self.get_serializer(pago).data)

    @transaction.atomic
    @action(detail=True, methods=["post"], url_path="reembolsar")
    def reembolsar(self, request, pk=None):
        motivo = str(request.data.get("motivo", "")).strip()
        if not motivo or len(motivo) > 500:
            raise ValidationError({"motivo": "Indica un motivo de hasta 500 caracteres."})
        inicial = get_object_or_404(Pago, pk=pk)
        pedido = get_object_or_404(Pedido.objects.select_for_update(), pk=inicial.pedido_id)
        pago = get_object_or_404(Pago.objects.select_for_update(), pk=pk)
        pago.pedido = pedido
        reembolsar_pago(pago, motivo, request.user)
        if pedido.estado not in {"ENTREGADO", "CANCELADO"}:
            cancelar_pedido(pedido, motivo)
        return Response(self.get_serializer(pago).data)

    @action(detail=False, methods=["get"], url_path="reporte-ventas")
    def reporte_ventas(self, request):
        from .reporting import periodo, ventas
        desde, hasta = periodo(request)
        return Response(ventas(desde, hasta))

    @action(detail=False, methods=["post"], url_path="conciliacion")
    def conciliacion(self, request):
        from .reporting import conciliar
        return Response(conciliar(request))


class NotificacionesView(APIView):
    def get(self, request):
        valor = request.query_params.get("despues", "0")
        if not valor.isdigit():
            raise ValidationError({"despues": "Usa un ID entero."})
        qs = Notificacion.objects.filter(id__gt=int(valor))
        if request.user.rol in {"cocina", "mesero"}:
            qs = qs.filter(tipo="PEDIDO_LISTO")
        return Response(list(qs.order_by("id").values("id", "pedido_id", "tipo", "mensaje", "creado_en")[:100]))


class WebhookQRView(APIView):
    """Contrato para un adaptador bancario; desactivado sin secreto configurado."""
    permission_classes = [AllowAny]
    authentication_classes = []

    @transaction.atomic
    def post(self, request):
        secret = settings.QR_WEBHOOK_SECRET
        if not secret:
            return Response({"detail": "Integración QR no configurada."}, status=503)
        firma = hmac.new(secret.encode(), request.body, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(firma, request.headers.get("X-QR-Signature", "")):
            return Response({"detail": "Firma inválida."}, status=403)
        from rest_framework import serializers

        class EventoSerializer(serializers.Serializer):
            evento = serializers.CharField(max_length=120)
            pago_id = serializers.IntegerField(min_value=1)
            monto = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=Decimal("0.01"))
            estado = serializers.ChoiceField(choices=["COMPLETADO"])
            referencia_qr = serializers.CharField(max_length=255)

        entrada = EventoSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        datos = entrada.validated_data
        inicial = get_object_or_404(Pago, pk=datos["pago_id"])
        pedido = get_object_or_404(Pedido.objects.select_for_update(), pk=inicial.pedido_id)
        pago = get_object_or_404(Pago.objects.select_for_update(), pk=inicial.pk)
        pago.pedido = pedido
        if pago.metodo != "QR" or pago.monto != datos["monto"] or pago.referencia_qr != datos["referencia_qr"]:
            raise ValidationError({"pago": "El evento no coincide con el pago QR registrado."})
        previo = Pago.objects.filter(evento_proveedor=datos["evento"]).first()
        if previo and previo.pk != pago.pk:
            raise ValidationError({"evento": "El evento pertenece a otro pago."})
        if pago.estado == "COMPLETADO":
            return Response({"estado": "COMPLETADO", "duplicado": True})
        confirmar_pago(pago)
        pago.evento_proveedor = datos["evento"]
        pago.save(update_fields=["evento_proveedor"])
        return Response({"estado": "COMPLETADO"})
