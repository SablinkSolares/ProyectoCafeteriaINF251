from decimal import Decimal

from django.db import models

from catalogo.models import Producto, Insumo


class Pedido(models.Model):
    """Pedido con máquina de estados finitos (RF2, RF3, RF5)."""

    class Estado(models.TextChoices):
        ESPERA = "ESPERA", "En espera"
        EN_PREPARACION = "EN_PREPARACION", "En preparación"
        LISTO = "LISTO", "Listo"
        ENTREGADO = "ENTREGADO", "Entregado"
        CANCELADO = "CANCELADO", "Cancelado"

    estado = models.CharField(
        max_length=20,
        choices=Estado.choices,
        default=Estado.ESPERA,
    )
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)
    reserva_registrada = models.BooleanField(default=False, editable=False)

    class Meta:
        db_table = "pedido"
        ordering = ["creado_en"]
        verbose_name = "pedido"
        verbose_name_plural = "pedidos"

    @property
    def total(self):
        """Suma exacta de subtotales con Decimal (RNF7)."""
        return sum((detalle.subtotal for detalle in self.detalles.all()), Decimal("0.00"))

    def __str__(self):
        return f"Pedido #{self.pk} ({self.get_estado_display()})"


class DetallePedido(models.Model):
    pedido = models.ForeignKey(
        Pedido,
        on_delete=models.CASCADE,
        related_name="detalles",
    )
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT)
    cantidad = models.PositiveIntegerField()
    # Se guarda el precio aplicado para que un cambio de catálogo no altere la venta.
    precio_unitario = models.DecimalField(max_digits=8, decimal_places=2)

    class Meta:
        db_table = "detalle_pedido"
        verbose_name = "detalle de pedido"
        verbose_name_plural = "detalles de pedido"

    @property
    def subtotal(self):
        return self.precio_unitario * self.cantidad

    def __str__(self):
        return f"{self.cantidad} x {self.producto.nombre}"


class ReservaInsumo(models.Model):
    class Estado(models.TextChoices):
        RESERVADA = "RESERVADA", "Reservada"
        CONSUMIDA = "CONSUMIDA", "Consumida"
        LIBERADA = "LIBERADA", "Liberada"

    pedido = models.ForeignKey(Pedido, on_delete=models.PROTECT, related_name="reservas_insumos")
    insumo = models.ForeignKey(Insumo, on_delete=models.PROTECT, related_name="reservas")
    cantidad = models.DecimalField(max_digits=12, decimal_places=3)
    estado = models.CharField(max_length=12, choices=Estado.choices, default=Estado.RESERVADA)

    class Meta:
        db_table = "reserva_insumo"
        constraints = [
            models.UniqueConstraint(fields=["pedido", "insumo"], name="reserva_pedido_insumo_unica"),
            models.CheckConstraint(condition=models.Q(cantidad__gt=0), name="reserva_insumo_cantidad_positiva"),
        ]


class Pago(models.Model):
    """Registro de pagos en efectivo o QR y sus reembolsos."""

    class Metodo(models.TextChoices):
        EFECTIVO = "EFECTIVO", "Efectivo"
        QR = "QR", "Código QR"

    class Estado(models.TextChoices):
        PENDIENTE = "PENDIENTE", "Pendiente"
        COMPLETADO = "COMPLETADO", "Completado"
        REEMBOLSADO = "REEMBOLSADO", "Reembolsado"
        FALLIDO = "FALLIDO", "Fallido"

    pedido = models.OneToOneField(
        Pedido,
        on_delete=models.PROTECT,
        related_name="pago",
    )

    monto = models.DecimalField(
        max_digits=10,
        decimal_places=2,
    )

    metodo = models.CharField(
        max_length=20,
        choices=Metodo.choices,
    )

    estado = models.CharField(
        max_length=20,
        choices=Estado.choices,
        default=Estado.PENDIENTE,
    )

    referencia_qr = models.CharField(
        max_length=255,
        blank=True,
    )

    creado_en = models.DateTimeField(auto_now_add=True)
    pagado_en = models.DateTimeField(null=True, blank=True)

    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "pago"
        ordering = ["-creado_en"]
        verbose_name = "pago"
        verbose_name_plural = "pagos"

    def __str__(self):
        return f"Pago #{self.pk} - Pedido #{self.pedido_id} - {self.metodo}"


class Reembolso(models.Model):
    pago = models.OneToOneField(Pago, on_delete=models.PROTECT, related_name="reembolso")
    fecha_hora_reembolso = models.DateTimeField(null=True, blank=True)
    importe_reembolsado = models.DecimalField(max_digits=10, decimal_places=2)
    tipo_reembolso = models.CharField(max_length=40, blank=True)
    motivo = models.TextField(blank=True)

    class Meta:
        db_table = "reembolso"
        constraints = [models.CheckConstraint(
            condition=models.Q(importe_reembolsado__gt=0), name="reembolso_importe_positivo"
        )]
