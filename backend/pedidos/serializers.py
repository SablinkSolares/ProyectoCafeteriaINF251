
from decimal import Decimal

from django.db import transaction
from rest_framework import serializers

from .models import DetallePedido, Pedido, Pago
from catalogo.models import Producto


class DetallePedidoSerializer(serializers.ModelSerializer):
    """Formato que consume la vista de cocina."""

    producto = serializers.CharField(source="producto.nombre", read_only=True)
    stock = serializers.DecimalField(source="producto.stock", max_digits=12, decimal_places=3, read_only=True)
    subtotal = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        read_only=True
    )

    class Meta:
        model = DetallePedido
        fields = [
            "id",
            "producto",
            "cantidad",
            "stock",
            "precio_unitario",
            "subtotal"
        ]




class DetallePedidoCreateSerializer(serializers.ModelSerializer):

    class Meta:
        model = DetallePedido
        # El cliente solo puede indicar el producto y la cantidad.
        # El precio siempre lo determina el backend.
        fields = ["producto", "cantidad"]

    def validate(self, attrs):
        producto = attrs["producto"]
        cantidad = attrs["cantidad"]

        if cantidad <= 0:
            raise serializers.ValidationError({
                "cantidad": "La cantidad debe ser mayor que cero."
            })

        if cantidad > producto.stock:
            raise serializers.ValidationError({
                "cantidad": (
                    f"Stock insuficiente de {producto.nombre} "
                    f"(disponible: {producto.stock})."
                )
            })

        return attrs



class PedidoSerializer(serializers.ModelSerializer):

    detalles = DetallePedidoSerializer(many=True, read_only=True)
    total = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        read_only=True
    )

    class Meta:
        model = Pedido
        fields = [
            "id",
            "estado",
            "creado_en",
            "actualizado_en",
            "total",
            "detalles"
        ]


class PedidoCreateSerializer(serializers.ModelSerializer):

    detalles = DetallePedidoCreateSerializer(
        many=True,
        allow_empty=False
    )

    class Meta:
        model = Pedido
        fields = ["id", "estado", "creado_en", "detalles"]
        read_only_fields = ["estado", "creado_en"]

    @transaction.atomic
    def create(self, validated_data):
        detalles = validated_data.pop("detalles")

        # Agrupar cantidades por producto.
        # Esto evita errores si un producto aparece varias veces.
        cantidades = {}

        for detalle in detalles:
            producto_id = detalle["producto"].id

            cantidades[producto_id] = (
                cantidades.get(producto_id, 0)
                + detalle["cantidad"]
            )

        productos = {}

        # Comprobar nuevamente el stock disponible.
        for producto_id, cantidad in cantidades.items():

            producto = Producto.objects.select_for_update().get(
                pk=producto_id
            )

            if cantidad > producto.stock:
                raise serializers.ValidationError({
                    "stock": (
                        f"Stock insuficiente de {producto.nombre}. "
                        f"Disponible: {producto.stock}, "
                        f"solicitado: {cantidad}."
                    )
                })

            productos[producto_id] = producto

        # Crear el pedido.
        pedido = Pedido.objects.create(**validated_data)

        # Crear los detalles del pedido.
        for detalle in detalles:
            producto = productos[detalle["producto"].id]

            DetallePedido.objects.create(
                pedido=pedido,
                producto=producto,
                cantidad=detalle["cantidad"],
                precio_unitario=producto.precio,
            )

        # Descontar el inventario.
        for producto_id, cantidad in cantidades.items():

            producto = productos[producto_id]
            producto.stock -= cantidad

            producto.save(update_fields=["stock"])

        return pedido


class PagoSerializer(serializers.ModelSerializer):

    class Meta:
        model = Pago
        fields = [
            "id",
            "pedido",
            "monto",
            "metodo",
            "estado",
            "referencia_qr",
            "motivo_reembolso",
            "creado_en",
            "pagado_en",
            "reembolsado_en",
            "actualizado_en",
        ]

        read_only_fields = [
            "id",
            "estado",
            "motivo_reembolso",
            "creado_en",
            "pagado_en",
            "reembolsado_en",
            "actualizado_en",
        ]

    def validate_monto(self, value):

        if value <= Decimal("0.00"):
            raise serializers.ValidationError(
                "El monto debe ser mayor que cero."
            )

        return value

    def validate(self, attrs):

        pedido = attrs["pedido"]
        monto = attrs["monto"]
        metodo = attrs["metodo"]

        if pedido.detalles.count() == 0:
            raise serializers.ValidationError({
                "pedido": "No se puede pagar un pedido sin productos."
            })

        if monto != pedido.total:
            raise serializers.ValidationError({
                "monto": (
                    f"El monto debe coincidir con el total "
                    f"del pedido: {pedido.total}."
                )
            })

        if Pago.objects.filter(pedido=pedido).exists():
            raise serializers.ValidationError({
                "pedido": "Este pedido ya tiene un registro de pago."
            })

        if (
            metodo == Pago.Metodo.EFECTIVO
            and attrs.get("referencia_qr")
        ):
            raise serializers.ValidationError({
                "referencia_qr": (
                    "La referencia QR solo corresponde "
                    "a pagos QR."
                )
            })

        return attrs
