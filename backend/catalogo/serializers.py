from decimal import Decimal
from django.db import transaction
from rest_framework import serializers
from .models import Categoria, Producto, Insumo, ProductoInsumo


class CategoriaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Categoria
        fields = ["id", "nombre", "imagen_carrusel"]


class ProductoMenuSerializer(serializers.ModelSerializer):
    """Información del menú público, sin existencias ni recetas internas."""
    categoria_nombre = serializers.CharField(source="categoria.nombre", read_only=True)

    class Meta:
        model = Producto
        fields = ["id", "nombre", "categoria", "categoria_nombre", "precio", "imagen"]


class ActualizarStockSerializer(serializers.Serializer):
    stock = serializers.IntegerField(min_value=0, max_value=999999999)
    stock_anterior = serializers.IntegerField(min_value=0, max_value=999999999, required=False)


class RecetaSerializer(serializers.ModelSerializer):
    nombre = serializers.CharField(source="insumo.nombre_insumo", read_only=True)
    unidad = serializers.CharField(source="insumo.unidad_medida", read_only=True)

    class Meta:
        model = ProductoInsumo
        fields = ["insumo", "nombre", "unidad", "cantidad_insumo_por_unidad"]
        validators = []


class ProductoSerializer(serializers.ModelSerializer):
    categoria_nombre = serializers.CharField(source="categoria.nombre", read_only=True)
    stock = serializers.DecimalField(max_digits=12, decimal_places=3, min_value=0, coerce_to_string=False, required=False)
    stock_disponible = serializers.IntegerField(read_only=True)
    insumos = RecetaSerializer(many=True, required=False)

    class Meta:
        model = Producto
        fields = ["id", "nombre", "categoria", "categoria_nombre", "precio", "stock", "stock_disponible", "imagen", "activo", "preparable", "insumos"]

    def validate_nombre(self, value):
        if not value.strip():
            raise serializers.ValidationError("El nombre es obligatorio.")
        return value.strip()

    def validate_precio(self, value):
        if value <= 0:
            raise serializers.ValidationError("El precio debe ser mayor que cero.")
        return value

    def validate(self, attrs):
        imagen = attrs.get("imagen", getattr(self.instance, "imagen", "")).strip()
        if not imagen:
            raise serializers.ValidationError({"imagen": "Debes agregar una imagen del producto."})
        if not imagen.startswith(("/images/", "/media/", "https://", "http://")):
            raise serializers.ValidationError({"imagen": "Usa una imagen subida, una ruta /images/ o una URL HTTP(S)."})
        preparable = attrs.get("preparable", getattr(self.instance, "preparable", False))
        recetas = attrs.get("insumos")
        if preparable and not (recetas if recetas is not None else self.instance and self.instance.insumos.exists()):
            raise serializers.ValidationError({"insumos": "Un producto preparable requiere al menos un insumo y su cantidad."})
        if recetas is not None and len({r["insumo"].pk for r in recetas}) != len(recetas):
            raise serializers.ValidationError({"insumos": "No repitas insumos en la receta."})
        stock = attrs.get("stock", getattr(self.instance, "stock", Decimal("0")))
        if not preparable and stock != int(stock):
            raise serializers.ValidationError({"stock": "Los productos terminados se cuentan en unidades enteras."})
        if self.instance and preparable != self.instance.preparable and self.instance.detallepedido_set.filter(pedido__estado__in=["ESPERA", "EN_PREPARACION", "LISTO"]).exists():
            raise serializers.ValidationError({"preparable": "Finaliza los pedidos activos antes de cambiar el tipo del producto."})
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        recetas = validated_data.pop("insumos", [])
        producto = Producto.objects.create(**validated_data)
        for receta in recetas:
            ProductoInsumo.objects.create(producto=producto, **receta)
        return producto

    @transaction.atomic
    def update(self, instance, validated_data):
        instance = Producto.objects.select_for_update().get(pk=instance.pk)
        recetas = validated_data.pop("insumos", None)
        instance = super().update(instance, validated_data)
        if recetas is not None:
            instance.insumos.all().delete()
            for receta in recetas:
                ProductoInsumo.objects.create(producto=instance, **receta)
        return instance


class InsumoSerializer(serializers.ModelSerializer):
    reservado = serializers.DecimalField(max_digits=12, decimal_places=3, read_only=True)
    disponible = serializers.DecimalField(max_digits=12, decimal_places=3, read_only=True)

    class Meta:
        model = Insumo
        fields = ["id", "nombre_insumo", "unidad_medida", "cantidad_stock", "reservado", "disponible"]

    def validate(self, attrs):
        if self.instance and attrs.get("cantidad_stock", self.instance.cantidad_stock) < self.instance.reservado:
            raise serializers.ValidationError({"cantidad_stock": "El stock físico no puede ser menor que la cantidad reservada."})
        return attrs
