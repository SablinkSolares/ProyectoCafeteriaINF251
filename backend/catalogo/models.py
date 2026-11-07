
from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models, transaction


class Categoria(models.Model):
    """Bebidas y acompañamientos (RF1)."""

    nombre = models.CharField(max_length=80, unique=True)
    imagen_carrusel = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        db_table = "categoria"
        ordering = ["nombre"]
        verbose_name = "categoría"
        verbose_name_plural = "categorías"

    def __str__(self):
        return self.nombre


class Producto(models.Model):
    """Producto ofrecido con precio decimal exacto y stock."""

    nombre = models.CharField(max_length=120)
    categoria = models.ForeignKey(
        Categoria,
        on_delete=models.PROTECT,
        related_name="productos",
    )
    precio = models.DecimalField(max_digits=8, decimal_places=2)
    imagen = models.CharField(max_length=500, blank=True, default="")
    activo = models.BooleanField(default=True)
    preparable = models.BooleanField(default=False)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "producto"
        ordering = ["nombre"]
        verbose_name = "producto"
        verbose_name_plural = "productos"
        indexes = [
            models.Index(
                fields=["categoria"],
                name="producto_categoria_idx",
            ),
            models.Index(
                fields=["precio"],
                name="producto_precio_idx",
            ),
        ]

    def __init__(self, *args, **kwargs):
        stock = kwargs.pop("stock", None)
        super().__init__(*args, **kwargs)
        if stock is not None:
            self._stock_pendiente = stock

    @transaction.atomic
    def save(self, *args, **kwargs):
        stock = getattr(self, "_stock_pendiente", None)
        update_fields = kwargs.get("update_fields")
        if update_fields is not None and "stock" in update_fields:
            kwargs["update_fields"] = set(update_fields) - {"stock"}
            if not kwargs["update_fields"]:
                kwargs["update_fields"] = {"actualizado_en"}
        super().save(*args, **kwargs)
        existencia, _ = ExistenciaProducto.objects.get_or_create(producto=self)
        if stock is not None:
            existencia.cantidad_stock = stock
            existencia.save(update_fields=["cantidad_stock"])
            del self._stock_pendiente
        self._state.fields_cache.pop("existencia", None)

    def __str__(self):
        return f"{self.nombre} ({self.categoria.nombre})"

    @property
    def stock(self):
        return self.existencia.cantidad_stock

    @stock.setter
    def stock(self, value):
        self._stock_pendiente = value

    @property
    def stock_disponible(self):
        if not self.activo:
            return 0
        if not self.preparable:
            return int(self.stock)
        recetas = list(self.insumos.all())
        if not recetas:
            return 0
        return min(int(max(Decimal("0"), r.insumo.disponible) / r.cantidad_insumo_por_unidad) for r in recetas)


class ExistenciaProducto(models.Model):
    producto = models.OneToOneField(
        Producto, on_delete=models.CASCADE, related_name="existencia"
    )
    unidad_medida = models.CharField(max_length=40, default="unidad")
    cantidad_stock = models.DecimalField(
        max_digits=12, decimal_places=3, default=0,
        validators=[MinValueValidator(Decimal("0"))],
    )

    class Meta:
        db_table = "existencia_producto"
        constraints = [models.CheckConstraint(
            condition=models.Q(cantidad_stock__gte=0), name="existencia_stock_no_negativo"
        )]


class Insumo(models.Model):
    nombre_insumo = models.CharField(max_length=120)
    unidad_medida = models.CharField(max_length=40)
    cantidad_stock = models.DecimalField(
        max_digits=12, decimal_places=3, default=0,
        validators=[MinValueValidator(Decimal("0"))],
    )

    class Meta:
        db_table = "insumo"
        constraints = [models.CheckConstraint(
            condition=models.Q(cantidad_stock__gte=0), name="insumo_stock_no_negativo"
        )]

    def __str__(self):
        return self.nombre_insumo

    @property
    def reservado(self):
        return self.reservas.filter(estado="RESERVADA").aggregate(total=models.Sum("cantidad"))["total"] or Decimal("0")

    @property
    def disponible(self):
        return self.cantidad_stock - self.reservado


class ProductoInsumo(models.Model):
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name="insumos")
    insumo = models.ForeignKey(Insumo, on_delete=models.PROTECT, related_name="productos")
    cantidad_insumo_por_unidad = models.DecimalField(
        max_digits=12, decimal_places=3,
        validators=[MinValueValidator(Decimal("0.001"))],
    )

    class Meta:
        db_table = "producto_insumo"
        constraints = [
            models.UniqueConstraint(fields=["producto", "insumo"], name="producto_insumo_unico"),
            models.CheckConstraint(
                condition=models.Q(cantidad_insumo_por_unidad__gt=0),
                name="producto_insumo_cantidad_positiva",
            ),
        ]


class ConfiguracionPago(models.Model):
    qr_habilitado = models.BooleanField(default=True)
    imagen_qr = models.CharField(max_length=500, blank=True, default="")
