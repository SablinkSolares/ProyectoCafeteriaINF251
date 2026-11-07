from decimal import Decimal
from django.db import transaction
from rest_framework import serializers
from catalogo.models import Producto
from .models import DetallePedido, Pedido, Pago
from .insumos import reservar_insumos


class DetallePedidoSerializer(serializers.ModelSerializer):
    producto = serializers.CharField(source="producto.nombre", read_only=True)
    producto_id = serializers.IntegerField(read_only=True)
    stock = serializers.IntegerField(source="producto.stock_disponible", read_only=True)
    subtotal = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = DetallePedido
        fields = ["id", "producto", "producto_id", "cantidad", "stock", "precio_unitario", "subtotal", "preparable"]


class PagoSerializer(serializers.ModelSerializer):
    motivo_reembolso = serializers.CharField(source="reembolso.motivo", read_only=True, default="")
    reembolsado_en = serializers.DateTimeField(source="reembolso.fecha_hora_reembolso", read_only=True, default=None)
    cambio = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    creado_por_nombre = serializers.CharField(source="creado_por.username", read_only=True, default=None)
    verificado_por_nombre = serializers.CharField(source="verificado_por.username", read_only=True, default=None)

    class Meta:
        model = Pago
        fields = ["id", "pedido", "monto", "monto_recibido", "cambio", "metodo", "estado", "referencia_qr", "motivo_reembolso", "creado_en", "pagado_en", "reembolsado_en", "creado_por_nombre", "verificado_por_nombre"]
        read_only_fields = ["estado", "pagado_en", "creado_en"]

    def validate(self, attrs):
        pedido = attrs["pedido"]
        monto = attrs["monto"]
        recibido = attrs.get("monto_recibido") or monto
        if monto <= 0 or monto != pedido.total:
            raise serializers.ValidationError({"monto": "El monto debe coincidir con el total positivo del pedido."})
        if attrs["metodo"] == Pago.Metodo.QR:
            if not attrs.get("referencia_qr", "").strip():
                raise serializers.ValidationError({"referencia_qr": "Indica la referencia del comprobante QR."})
            if recibido != monto:
                raise serializers.ValidationError({"monto_recibido": "El pago QR debe ser exacto."})
        elif recibido < monto:
            raise serializers.ValidationError({"monto_recibido": "El monto recibido debe cubrir el total."})
        elif attrs.get("referencia_qr"):
            raise serializers.ValidationError({"referencia_qr": "La referencia solo corresponde a pagos QR."})
        attrs["monto_recibido"] = recibido
        return attrs


class PedidoSerializer(serializers.ModelSerializer):
    detalles = DetallePedidoSerializer(many=True, read_only=True)
    pago = PagoSerializer(read_only=True, default=None)
    total = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    registrado_por_nombre = serializers.CharField(source="registrado_por.username", read_only=True, default=None)
    preparado_por_nombre = serializers.CharField(source="preparado_por.username", read_only=True, default=None)
    listo_por_nombre = serializers.CharField(source="listo_por.username", read_only=True, default=None)
    entregado_por_nombre = serializers.CharField(source="entregado_por.username", read_only=True, default=None)
    reemplazos = serializers.PrimaryKeyRelatedField(many=True, read_only=True)

    class Meta:
        model = Pedido
        fields = ["id", "estado", "mesa", "observaciones", "creado_en", "actualizado_en", "total", "detalles", "pago", "reserva_registrada", "registrado_por_nombre", "preparado_por_nombre", "listo_por_nombre", "entregado_por_nombre", "en_preparacion_en", "listo_en", "entregado_en", "cancelado_en", "motivo_cancelacion", "pedido_original", "motivo_cambio", "reemplazos"]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get("request")
        if request and request.user.rol in {"cocina", "mesero"}:
            # El personal operativo solo necesita conocer si está pagado.
            data["pago"] = {"estado": data["pago"]["estado"]} if data["pago"] else None
        return data


class LineaCreateSerializer(serializers.Serializer):
    producto = serializers.PrimaryKeyRelatedField(queryset=Producto.objects.filter(activo=True))
    cantidad = serializers.IntegerField(min_value=1, max_value=10000)


class PedidoCreateSerializer(serializers.ModelSerializer):
    detalles = LineaCreateSerializer(many=True, allow_empty=False)
    mesa = serializers.IntegerField(min_value=1, max_value=10)

    class Meta:
        model = Pedido
        fields = ["id", "mesa", "observaciones", "detalles"]

    @transaction.atomic
    def create(self, validated_data):
        lineas = validated_data.pop("detalles")
        cantidades = {}
        for linea in lineas:
            pk = linea["producto"].pk
            cantidades[pk] = cantidades.get(pk, 0) + linea["cantidad"]
        productos = {p.pk: p for p in Producto.objects.select_for_update().filter(pk__in=cantidades).order_by("pk")}
        total = sum((productos[pk].precio * n for pk, n in cantidades.items()), Decimal("0"))
        if total > Decimal("99999999.99"):
            raise serializers.ValidationError({"total": "El pedido excede el importe máximo permitido."})
        for pk, cantidad in cantidades.items():
            producto = productos[pk]
            if not producto.activo:
                raise serializers.ValidationError({"producto": f"{producto.nombre} está desactivado."})
            if producto.preparable and not producto.insumos.exists():
                raise serializers.ValidationError({"insumos": f"{producto.nombre} no tiene receta."})
            if cantidad > producto.stock_disponible:
                raise serializers.ValidationError({"stock": f"Stock insuficiente de {producto.nombre}. Disponible: {producto.stock_disponible}."})
        pedido = Pedido.objects.create(reserva_registrada=True, **validated_data)
        reservar_insumos(pedido, {pk: n for pk, n in cantidades.items() if productos[pk].preparable})
        for pk, cantidad in cantidades.items():
            producto = productos[pk]
            DetallePedido.objects.create(pedido=pedido, producto=producto, cantidad=cantidad, precio_unitario=producto.precio, preparable=producto.preparable)
            if not producto.preparable:
                producto.stock -= cantidad
                producto.save(update_fields=["stock"])
        return pedido
