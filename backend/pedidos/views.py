

from django.db import transaction
from django.utils import timezone
from django.shortcuts import get_object_or_404
from decimal import Decimal
from django.db.models import Sum, Count
from django.utils.dateparse import parse_date
from rest_framework import serializers, status, viewsets
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from dinocafe.permissions import EsAdministrador

from catalogo.models import Producto
from .models import Pedido, Pago
from .serializers import PedidoCreateSerializer, PedidoSerializer, PagoSerializer


# Máquina de estados de RF5.
TRANSICIONES = {
    Pedido.Estado.ESPERA: (
        Pedido.Estado.EN_PREPARACION,
        {"administrador", "cocina"}
    ),
    Pedido.Estado.EN_PREPARACION: (
        Pedido.Estado.LISTO,
        {"administrador", "cocina"}
    ),
    Pedido.Estado.LISTO: (
        Pedido.Estado.ENTREGADO,
        {"administrador", "mesero"}
    ),
}


class PedidoViewSet(viewsets.ModelViewSet):

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
            lista = [e.strip() for e in estados.split(",") if e.strip()]
            qs = qs.filter(estado__in=lista)

        return qs

    def get_serializer_class(self):
        if self.action == "create":
            return PedidoCreateSerializer
        return PedidoSerializer

    def create(self, request, *args, **kwargs):

        if request.user.rol not in {"administrador", "mesero"}:
            raise PermissionDenied(
                "Solo el mesero o el administrador registran pedidos."
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        pedido = serializer.save()

        return Response(
            PedidoSerializer(
                pedido,
                context=self.get_serializer_context()
            ).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["patch"], url_path="estado")
    def cambiar_estado(self, request, pk=None):

        pedido = self.get_object()
        nuevo = request.data.get("estado")

        if nuevo not in Pedido.Estado.values:
            raise ValidationError({
                "estado": (
                    "Estado no válido. Usa ESPERA, EN_PREPARACION, "
                    "LISTO o ENTREGADO."
                )
            })

        transicion = TRANSICIONES.get(pedido.estado)

        if not transicion:
            raise ValidationError({
                "estado": "El pedido ya fue entregado; no admite más cambios."
            })

        siguiente, roles = transicion

        if request.user.rol not in roles:
            raise PermissionDenied(
                f"El rol {request.user.rol} no puede cambiar "
                f"de {pedido.estado} a {nuevo}."
            )

        if nuevo != siguiente:
            raise ValidationError({
                "estado": (
                    f"Transición inválida: {pedido.estado} → {nuevo}. "
                    f"Debe ser {siguiente}."
                )
            })

        pedido.estado = nuevo
        pedido.save(update_fields=["estado", "actualizado_en"])

        return Response(
            PedidoSerializer(
                pedido,
                context=self.get_serializer_context()
            ).data
        )


class PagoViewSet(viewsets.GenericViewSet):

    serializer_class = PagoSerializer
    permission_classes = [IsAuthenticated]
    queryset = Pago.objects.select_related("pedido").all()

    def initial(self, request, *args, **kwargs):

        super().initial(request, *args, **kwargs)

        if request.user.rol not in {"administrador", "cajero"}:
            raise PermissionDenied(
                "Solo el administrador o el cajero pueden gestionar pagos."
            )

    def list(self, request):

        pagos = self.get_queryset()
        serializer = self.get_serializer(pagos, many=True)

        return Response(serializer.data)

    def retrieve(self, request, pk=None):

        pago = self.get_object()

        return Response(self.get_serializer(pago).data)

    def create(self, request, *args, **kwargs):

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        metodo = serializer.validated_data["metodo"]

        with transaction.atomic():

            if metodo == Pago.Metodo.EFECTIVO:
                pago = serializer.save(
                    estado=Pago.Estado.COMPLETADO,
                    pagado_en=timezone.now(),
                )
            else:
                pago = serializer.save(
                    estado=Pago.Estado.PENDIENTE,
                )

        return Response(
            self.get_serializer(pago).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"], url_path="confirmar")
    def confirmar(self, request, pk=None):

        with transaction.atomic():

            pago = get_object_or_404(
                Pago.objects.select_for_update(),
                pk=pk,
            )

            if pago.estado != Pago.Estado.PENDIENTE:
                raise ValidationError({
                    "estado": "Solo se pueden confirmar pagos pendientes."
                })

            pago.estado = Pago.Estado.COMPLETADO
            pago.pagado_en = timezone.now()

            pago.save(update_fields=[
                "estado",
                "pagado_en",
                "actualizado_en",
            ])

        return Response(self.get_serializer(pago).data)

    @action(detail=True, methods=["post"], url_path="reembolsar")
    def reembolsar(self, request, pk=None):

        motivo = request.data.get("motivo", "").strip()

        if not motivo:
            raise ValidationError({
                "motivo": "Debes indicar el motivo del reembolso."
            })

        with transaction.atomic():

            pago = get_object_or_404(
                Pago.objects.select_for_update(),
                pk=pk,
            )

            if pago.estado != Pago.Estado.COMPLETADO:
                raise ValidationError({
                    "estado": "Solo se pueden reembolsar pagos completados."
                })

            # Obtener los productos y cantidades del pedido.
            detalles = pago.pedido.detalles.all()

            cantidades = {}

            for detalle in detalles:
                producto_id = detalle.producto_id

                cantidades[producto_id] = (
                    cantidades.get(producto_id, 0)
                    + detalle.cantidad
                )

            # Bloquear los productos y devolver las unidades.
            productos = Producto.objects.select_for_update().filter(
                pk__in=cantidades.keys()
            )

            for producto in productos:
                producto.stock += cantidades[producto.id]

                producto.save(update_fields=[
                    "stock",
                    "actualizado_en",
                ])

            # Actualizar el pago.
            pago.estado = Pago.Estado.REEMBOLSADO
            pago.motivo_reembolso = motivo
            pago.reembolsado_en = timezone.now()

            pago.save(update_fields=[
                "estado",
                "motivo_reembolso",
                "reembolsado_en",
                "actualizado_en",
            ])

        return Response(self.get_serializer(pago).data)

    @action(detail=False, methods=["post"], url_path="conciliacion")
    def conciliacion(self, request):

        # Validar fecha.
        fecha = parse_date(request.data.get("fecha", ""))

        if not fecha:
            raise ValidationError({
                "fecha": "Debes proporcionar una fecha válida (YYYY-MM-DD)."
            })

        # Validar montos reales recibidos.
        campo_decimal = serializers.DecimalField(
            max_digits=12,
            decimal_places=2,
            min_value=Decimal("0.00")
        )

        try:
            efectivo_real = campo_decimal.run_validation(
                request.data.get("efectivo_real")
            )

            qr_real = campo_decimal.run_validation(
                request.data.get("qr_real")
            )

        except ValidationError as error:
            raise ValidationError({
                "montos": error.detail
            })

        # Métodos de pago que se van a conciliar.
        metodos = {
            Pago.Metodo.EFECTIVO: "efectivo",
            Pago.Metodo.QR: "qr",
        }

        # Inicializar resultados.
        ventas = {
            metodo: {"cantidad": 0, "total": Decimal("0.00")}
            for metodo in metodos.values()
        }

        reembolsos = {
            metodo: {"cantidad": 0, "total": Decimal("0.00")}
            for metodo in metodos.values()
        }

        # Agregar ventas realizadas en la fecha.
        # Se incluyen pagos completados y reembolsados porque
        # la venta original sí ocurrió en la fecha indicada.
        ventas_db = (
            Pago.objects
            .filter(
                pagado_en__date=fecha,
                estado__in=[
                    Pago.Estado.COMPLETADO,
                    Pago.Estado.REEMBOLSADO,
                ]
            )
            .values("metodo")
            .annotate(
                total=Sum("monto"),
                cantidad=Count("id")
            )
        )

        for registro in ventas_db:
            metodo = metodos[registro["metodo"]]

            ventas[metodo] = {
                "cantidad": registro["cantidad"],
                "total": registro["total"] or Decimal("0.00"),
            }

        # Agregar reembolsos realizados en la fecha.
        reembolsos_db = (
            Pago.objects
            .filter(
                reembolsado_en__date=fecha,
                estado=Pago.Estado.REEMBOLSADO,
            )
            .values("metodo")
            .annotate(
                total=Sum("monto"),
                cantidad=Count("id")
            )
        )

        for registro in reembolsos_db:
            metodo = metodos[registro["metodo"]]

            reembolsos[metodo] = {
                "cantidad": registro["cantidad"],
                "total": registro["total"] or Decimal("0.00"),
            }

        # Calcular ventas netas y diferencias.
        montos_reales = {
            "efectivo": efectivo_real,
            "qr": qr_real,
        }

        ventas_netas = {}
        diferencias = {}

        for metodo in metodos.values():

            neto = (
                ventas[metodo]["total"]
                - reembolsos[metodo]["total"]
            )

            diferencia = montos_reales[metodo] - neto

            ventas_netas[metodo] = neto
            diferencias[metodo] = diferencia

        # Calcular totales generales.
        total_ventas = sum(
            (dato["total"] for dato in ventas.values()),
            Decimal("0.00")
        )

        total_reembolsos = sum(
            (dato["total"] for dato in reembolsos.values()),
            Decimal("0.00")
        )

        total_neto = sum(ventas_netas.values(), Decimal("0.00"))

        total_real = sum(montos_reales.values(), Decimal("0.00"))

        total_diferencia = total_real - total_neto

        # Determinar si la caja cuadra.
        cuadra = all(
            diferencia == Decimal("0.00")
            for diferencia in diferencias.values()
        )

        # Formatear los importes como cadenas decimales.
        def formato(valor):
            return format(valor, ".2f")

        return Response({
            "fecha": fecha.isoformat(),

            "ventas": {
                metodo: {
                    "cantidad": ventas[metodo]["cantidad"],
                    "total": formato(ventas[metodo]["total"]),
                }
                for metodo in metodos.values()
            },

            "total_ventas": formato(total_ventas),

            "reembolsos": {
                metodo: {
                    "cantidad": reembolsos[metodo]["cantidad"],
                    "total": formato(reembolsos[metodo]["total"]),
                }
                for metodo in metodos.values()
            },

            "total_reembolsos": formato(total_reembolsos),

            "ventas_netas": {
                metodo: formato(ventas_netas[metodo])
                for metodo in metodos.values()
            },

            "total_neto": formato(total_neto),

            "recaudado_real": {
                metodo: formato(montos_reales[metodo])
                for metodo in metodos.values()
            },

            "total_real": formato(total_real),

            "diferencias": {
                metodo: formato(diferencias[metodo])
                for metodo in metodos.values()
            },

            "total_diferencia": formato(total_diferencia),

            "cuadra": cuadra,
        })
