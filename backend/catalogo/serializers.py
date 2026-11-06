
from decimal import Decimal

from rest_framework import serializers

from .models import Categoria, Producto


class CategoriaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Categoria
        fields = ["id", "nombre"]


class ProductoSerializer(serializers.ModelSerializer):
    categoria_nombre = serializers.CharField(
        source="categoria.nombre",
        read_only=True
    )

    stock = serializers.DecimalField(
        max_digits=12,
        decimal_places=3,
        required=False
    )

    class Meta:
        model = Producto
        fields = [
            "id",
            "nombre",
            "categoria",
            "categoria_nombre",
            "precio",
            "stock",
        ]

    def validate_nombre(self, value):
        if not value.strip():
            raise serializers.ValidationError(
                "El nombre del producto es obligatorio."
            )
        return value.strip()

    def validate_precio(self, value):
        if value <= 0:
            raise serializers.ValidationError(
                "El precio debe ser mayor que cero."
            )
        return value

    def validate_stock(self, value):
        if value < Decimal("0"):
            raise serializers.ValidationError(
                "El stock no puede ser negativo."
            )
        return value

    def create(self, validated_data):
        stock = validated_data.pop("stock", Decimal("0"))

        producto = Producto(**validated_data)
        producto.stock = stock
        producto.save()

        return producto

    def update(self, instance, validated_data):
        stock = validated_data.pop("stock", None)

        for atributo, valor in validated_data.items():
            setattr(instance, atributo, valor)

        if stock is not None:
            instance.stock = stock

        instance.save()

        return instance

