from rest_framework import serializers

from .models import DetallePedido, Pedido


class DetallePedidoSerializer(serializers.ModelSerializer):
    """Formato que consume la vista de cocina de Carlos (S1-T08)."""

    producto = serializers.CharField(source="producto.nombre", read_only=True)
    stock = serializers.IntegerField(source="producto.stock", read_only=True)
    subtotal = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = DetallePedido
        fields = ["id", "producto", "cantidad", "stock", "precio_unitario", "subtotal"]


class DetallePedidoCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = DetallePedido
        fields = ["producto", "cantidad", "precio_unitario"]
        extra_kwargs = {"precio_unitario": {"required": False}}

    def validate(self, attrs):
        producto = attrs["producto"]
        cantidad = attrs["cantidad"]
        if cantidad <= 0:
            raise serializers.ValidationError({"cantidad": "La cantidad debe ser mayor que cero."})
        if cantidad > producto.stock:
            raise serializers.ValidationError(
                {"cantidad": f"Stock insuficiente de {producto.nombre} (disponible: {producto.stock})."}
            )
        attrs.setdefault("precio_unitario", producto.precio)
        return attrs


class PedidoSerializer(serializers.ModelSerializer):
    detalles = DetallePedidoSerializer(many=True, read_only=True)
    total = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = Pedido
        fields = ["id", "estado", "creado_en", "actualizado_en", "total", "detalles"]


class PedidoCreateSerializer(serializers.ModelSerializer):
    detalles = DetallePedidoCreateSerializer(many=True)

    class Meta:
        model = Pedido
        fields = ["id", "estado", "creado_en", "detalles"]
        read_only_fields = ["estado", "creado_en"]

    def create(self, validated_data):
        detalles = validated_data.pop("detalles")
        pedido = Pedido.objects.create(**validated_data)
        for detalle in detalles:
            DetallePedido.objects.create(pedido=pedido, **detalle)
        return pedido
