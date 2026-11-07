from decimal import Decimal

from django.db import models
from django.conf import settings

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
    mesa = models.PositiveSmallIntegerField(default=1)
    observaciones = models.CharField(max_length=500, blank=True)
    motivo_cancelacion = models.CharField(max_length=500, blank=True)
    pedido_original = models.ForeignKey("self", null=True, blank=True, on_delete=models.PROTECT, related_name="reemplazos")
    motivo_cambio = models.CharField(max_length=500, blank=True)
    registrado_por = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="pedidos_registrados")
    preparado_por = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="pedidos_preparados")
    listo_por = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="pedidos_listos")
    entregado_por = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="pedidos_entregados")
    en_preparacion_en = models.DateTimeField(null=True, blank=True)
    listo_en = models.DateTimeField(null=True, blank=True)
    entregado_en = models.DateTimeField(null=True, blank=True)
    cancelado_en = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "pedido"
        ordering = ["creado_en"]
        verbose_name = "pedido"
        verbose_name_plural = "pedidos"
        constraints = [models.CheckConstraint(condition=models.Q(mesa__gte=1, mesa__lte=10), name="pedido_mesa_valida")]
        indexes = [models.Index(fields=["creado_en", "estado"], name="pedido_fecha_estado_idx")]

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
    preparable = models.BooleanField(default=False)

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
    monto_recibido = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    creado_por = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="pagos_creados")
    verificado_por = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="pagos_verificados")
    evento_proveedor = models.CharField(max_length=120, blank=True, unique=True, null=True)

    @property
    def cambio(self):
        return (self.monto_recibido or self.monto) - self.monto

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
    registrado_por = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="reembolsos_registrados")

    class Meta:
        db_table = "reembolso"
        constraints = [models.CheckConstraint(
            condition=models.Q(importe_reembolsado__gt=0), name="reembolso_importe_positivo"
        )]


class Notificacion(models.Model):
    pedido = models.ForeignKey(Pedido, on_delete=models.PROTECT, related_name="notificaciones")
    tipo = models.CharField(max_length=30)
    mensaje = models.CharField(max_length=300)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-id"]
        constraints = [models.UniqueConstraint(fields=["pedido", "tipo"], name="notificacion_pedido_tipo_unica")]


class ReportePDF(models.Model):
    tipo = models.CharField(max_length=30)
    desde = models.DateField()
    hasta = models.DateField()
    generado_por = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    generado_en = models.DateTimeField(auto_now_add=True)
    resumen = models.JSONField(default=dict)
    contenido = models.BinaryField(editable=False)
    sha256 = models.CharField(max_length=64)

    class Meta:
        ordering = ["-id"]
