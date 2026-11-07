"""Operaciones de inventario y pagos bajo el bloqueo del pedido."""
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from catalogo.models import Producto
from .models import Pedido, Pago, Reembolso, ReservaInsumo, Notificacion


def notificar(pedido, tipo, mensaje):
    Notificacion.objects.get_or_create(pedido=pedido, tipo=tipo, defaults={"mensaje": mensaje})


def confirmar_pago(pago, usuario=None):
    # El llamador bloquea primero el pedido y después el pago.
    if pago.estado == Pago.Estado.COMPLETADO:
        return pago
    if pago.estado != Pago.Estado.PENDIENTE or pago.pedido.estado != Pedido.Estado.ENTREGADO:
        raise ValidationError({"pago": "El pago o el pedido ya no admite confirmación."})
    pago.estado = Pago.Estado.COMPLETADO
    pago.pagado_en = timezone.now()
    pago.verificado_por = usuario
    pago.save(update_fields=["estado", "pagado_en", "verificado_por", "actualizado_en"])
    pedido = pago.pedido
    notificar(pedido, "PAGO_REALIZADO", f"Pago realizado: pedido #{pedido.pk}, mesa {pedido.mesa}, Bs {pago.monto} ({pago.metodo}).")
    return pago


def reembolsar_pago(pago, motivo, usuario):
    if pago.estado != Pago.Estado.COMPLETADO:
        raise ValidationError({"pago": "Solo se reembolsan pagos completados."})
    Reembolso.objects.create(pago=pago, motivo=motivo, registrado_por=usuario, fecha_hora_reembolso=timezone.now(), importe_reembolsado=pago.monto, tipo_reembolso="total")
    pago.estado = Pago.Estado.REEMBOLSADO
    pago.save(update_fields=["estado", "actualizado_en"])
    notificar(pago.pedido, "REEMBOLSO", f"Reembolso del pedido #{pago.pedido_id}: Bs {pago.monto}.")


def cancelar_pedido(pedido, motivo):
    if pedido.estado in {Pedido.Estado.ENTREGADO, Pedido.Estado.CANCELADO}:
        raise ValidationError({"pedido": "No se puede cancelar un pedido entregado o cancelado."})
    if not pedido.reserva_registrada:
        raise ValidationError({"pedido": "El pedido histórico requiere conciliación manual de inventario."})
    pago = Pago.objects.select_for_update().filter(pedido=pedido).first()
    if pago and pago.estado == Pago.Estado.COMPLETADO:
        raise ValidationError({"pago": "Registra primero el reembolso del pago."})
    # Solo se repone lo que aún no ha entrado en preparación.
    if pedido.estado == Pedido.Estado.ESPERA:
        cantidades = {d.producto_id: d.cantidad for d in pedido.detalles.filter(preparable=False)}
        for producto in Producto.objects.select_for_update().filter(pk__in=cantidades).order_by("pk"):
            producto.stock += cantidades[producto.pk]
            producto.save(update_fields=["stock"])
        pedido.reservas_insumos.filter(estado=ReservaInsumo.Estado.RESERVADA).update(estado=ReservaInsumo.Estado.LIBERADA)
    if pago and pago.estado == Pago.Estado.PENDIENTE:
        pago.estado = Pago.Estado.FALLIDO
        pago.save(update_fields=["estado", "actualizado_en"])
    pedido.estado = Pedido.Estado.CANCELADO
    pedido.motivo_cancelacion = motivo
    pedido.cancelado_en = timezone.now()
    pedido.save(update_fields=["estado", "motivo_cancelacion", "cancelado_en", "actualizado_en"])
