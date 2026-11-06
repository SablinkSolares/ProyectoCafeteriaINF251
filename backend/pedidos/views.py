

from django.db import transaction
from django.utils import timezone
from django.shortcuts import get_object_or_404
from decimal import Decimal
from django.db.models import Sum, Count, F, DecimalField, ExpressionWrapper
from django.utils.dateparse import parse_date
from rest_framework import serializers, status, viewsets
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from dinocafe.permissions import EsAdministrador

from catalogo.models import Producto
from .models import Pedido, Pago, Reembolso, DetallePedido, ReservaInsumo
from .insumos import descontar_insumos
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

    def update(self, request, *args, **kwargs):
        raise ValidationError({"pedido": "Usa las acciones de preparación, entrega o cancelación para cambiar un pedido."})

    def destroy(self, request, *args, **kwargs):
        pedido = self.get_object()
        if pedido.reserva_registrada:
            raise ValidationError({"pedido": "No elimines pedidos con reservas; utiliza la opción de cancelar."})
        return super().destroy(request, *args, **kwargs)

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

    @transaction.atomic
    @action(detail=True, methods=["patch"], url_path="estado")
    def cambiar_estado(self, request, pk=None):

        pedido = get_object_or_404(Pedido.objects.select_for_update(), pk=pk)
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

    @action(detail=True, methods=["post"], url_path="cancelar")
    def cancelar(self, request, pk=None):
        if request.user.rol not in {"administrador", "mesero"}:
            raise PermissionDenied("Solo el mesero o el administrador pueden cancelar pedidos.")
        with transaction.atomic():
            pedido = get_object_or_404(Pedido.objects.select_for_update(), pk=pk)
            if pedido.estado not in {Pedido.Estado.ESPERA, Pedido.Estado.EN_PREPARACION, Pedido.Estado.LISTO}:
                raise ValidationError({"pedido": "Solo se pueden cancelar pedidos aún no entregados."})
            if not pedido.reserva_registrada:
                raise ValidationError({"pedido": "Este pedido es anterior al control de reservas. Revisa el inventario antes de resolverlo manualmente."})
            pago = Pago.objects.select_for_update().filter(pedido=pedido).first()
            if pago and pago.estado in {Pago.Estado.COMPLETADO, Pago.Estado.REEMBOLSADO}:
                raise ValidationError({"pedido": "Este pedido ya tiene un pago; debe revisarse el reembolso."})
            cantidades = {}
            for detalle in pedido.detalles.all():
                cantidades[detalle.producto_id] = cantidades.get(detalle.producto_id, 0) + detalle.cantidad
            for producto in Producto.objects.select_for_update().filter(pk__in=cantidades).order_by("pk"):
                producto.stock += cantidades[producto.pk]
                producto.save(update_fields=["stock"])
            pedido.reservas_insumos.filter(estado=ReservaInsumo.Estado.RESERVADA).update(estado=ReservaInsumo.Estado.LIBERADA)
            if pago and pago.estado == Pago.Estado.PENDIENTE:
                pago.estado = Pago.Estado.FALLIDO
                pago.save(update_fields=["estado", "actualizado_en"])
            pedido.estado = Pedido.Estado.CANCELADO
            pedido.save(update_fields=["estado", "actualizado_en"])
        return Response(PedidoSerializer(pedido, context=self.get_serializer_context()).data)


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

            pedido = get_object_or_404(Pedido.objects.select_for_update(), pk=serializer.validated_data["pedido"].pk)
            if pedido.estado != Pedido.Estado.ENTREGADO:
                raise ValidationError({"pedido": "El pedido debe estar entregado antes de registrar el pago."})
            if Pago.objects.filter(pedido=pedido).exists():
                raise ValidationError({"pedido": "Este pedido ya tiene un registro de pago."})

            if metodo == Pago.Metodo.EFECTIVO:
                descontar_insumos(pedido)
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
            pago_inicial = get_object_or_404(Pago.objects.only("pedido_id"), pk=pk)
            pedido = get_object_or_404(Pedido.objects.select_for_update(), pk=pago_inicial.pedido_id)
            pago = get_object_or_404(Pago.objects.select_for_update(), pk=pk, pedido=pedido)

            if pago.estado != Pago.Estado.PENDIENTE:
                raise ValidationError({
                    "estado": "Solo se pueden confirmar pagos pendientes."
                })

            if pedido.estado != Pedido.Estado.ENTREGADO:
                raise ValidationError({"pedido": "El pedido debe estar entregado antes de confirmar el pago."})

            descontar_insumos(pedido)
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

            # Un pedido nuevo ya entregado puede haberse consumido; un reembolso
            # no devuelve físicamente los productos. Se conserva el comportamiento
            # histórico de pedidos anteriores, cuyo stock no puede reconstruirse.
            if not pago.pedido.reserva_registrada:
                for producto in productos:
                    producto.stock += cantidades[producto.id]

                    producto.save(update_fields=[
                        "stock",
                        "actualizado_en",
                    ])

            # Actualizar el pago.
            pago.estado = Pago.Estado.REEMBOLSADO
            Reembolso.objects.create(
                pago=pago, motivo=motivo, fecha_hora_reembolso=timezone.now(),
                importe_reembolsado=pago.monto, tipo_reembolso="total",
            )

            pago.save(update_fields=[
                "estado",
                "actualizado_en",
            ])

        return Response(self.get_serializer(pago).data)

    @action(detail=False, methods=["get"], url_path="reporte-ventas")
    def reporte_ventas(self, request):
        if request.user.rol != "administrador":
            raise PermissionDenied("Solo el administrador puede consultar el reporte de ventas.")
        try:
            desde = parse_date(request.query_params.get("desde", ""))
            hasta = parse_date(request.query_params.get("hasta", ""))
        except (ValueError, TypeError):
            desde = hasta = None
        if not desde or not hasta or desde > hasta:
            raise ValidationError({"periodo": "Indica fechas válidas y verifica que Desde sea anterior o igual a Hasta."})

        pagos = Pago.objects.filter(
            estado__in=[Pago.Estado.COMPLETADO, Pago.Estado.REEMBOLSADO],
            pagado_en__date__gte=desde, pagado_en__date__lte=hasta,
        )
        ventas = pagos.aggregate(total=Sum("monto"), cantidad=Count("id"))
        reembolsos = Reembolso.objects.filter(
            pago__estado=Pago.Estado.REEMBOLSADO,
            fecha_hora_reembolso__date__gte=desde,
            fecha_hora_reembolso__date__lte=hasta,
        ).aggregate(total=Sum("importe_reembolsado"))
        lineas = DetallePedido.objects.filter(pedido__pago__in=pagos)
        subtotal = ExpressionWrapper(
            F("cantidad") * F("precio_unitario"),
            output_field=DecimalField(max_digits=20, decimal_places=2),
        )
        productos = list(lineas.values(
            "producto_id", "producto__nombre", "producto__categoria__nombre"
        ).annotate(unidades=Sum("cantidad"), total=Sum(subtotal)).order_by("producto__nombre", "producto_id"))
        categorias = list(lineas.values(
            "producto__categoria_id", "producto__categoria__nombre"
        ).annotate(unidades=Sum("cantidad"), total=Sum(subtotal)).order_by("producto__categoria__nombre"))
        bruto = ventas["total"] or Decimal("0.00")
        devuelto = reembolsos["total"] or Decimal("0.00")
        return Response({
            "desde": desde.isoformat(), "hasta": hasta.isoformat(),
            "cantidad_pagos": ventas["cantidad"],
            "total_ventas": format(bruto, ".2f"),
            "total_reembolsos": format(devuelto, ".2f"),
            "total_neto": format(bruto - devuelto, ".2f"),
            "productos": productos, "categorias": categorias,
        })

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
            Reembolso.objects
            .filter(
                fecha_hora_reembolso__date=fecha,
                pago__estado=Pago.Estado.REEMBOLSADO,
            )
            .values("pago__metodo")
            .annotate(
                total=Sum("importe_reembolsado"),
                cantidad=Count("id")
            )
        )

        for registro in reembolsos_db:
            metodo = metodos[registro["pago__metodo"]]

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
