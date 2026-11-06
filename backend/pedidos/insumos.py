"""Reservas y consumo de insumos. Se ejecutan dentro de una transacción."""
from collections import defaultdict
from decimal import Decimal

from django.db.models import Sum
from rest_framework.exceptions import ValidationError

from catalogo.models import Insumo, ProductoInsumo
from .models import ReservaInsumo


def cantidades_por_producto(detalles):
    cantidades = defaultdict(int)
    for detalle in detalles:
        cantidades[detalle.producto_id] += detalle.cantidad
    return cantidades


def calcular_receta(cantidades):
    requeridos = defaultdict(Decimal)
    recetas = ProductoInsumo.objects.select_for_update().filter(
        producto_id__in=cantidades
    ).order_by("producto_id", "insumo_id")
    for receta in recetas:
        requeridos[receta.insumo_id] += receta.cantidad_insumo_por_unidad * cantidades[receta.producto_id]
    return requeridos


def bloquear_y_comprobar(requeridos, descontar_reservas=True):
    insumos = list(Insumo.objects.select_for_update().filter(pk__in=requeridos).order_by("pk"))
    reservados = {}
    if descontar_reservas:
        reservados = dict(ReservaInsumo.objects.filter(
            insumo_id__in=requeridos, estado=ReservaInsumo.Estado.RESERVADA
        ).values_list("insumo_id").annotate(total=Sum("cantidad")))
    faltantes = []
    for insumo in insumos:
        disponible = insumo.cantidad_stock - reservados.get(insumo.pk, Decimal("0"))
        if disponible < requeridos[insumo.pk]:
            faltantes.append(f"{insumo.nombre_insumo}: disponible {max(disponible, Decimal('0'))} "
                             f"{insumo.unidad_medida}, requerido {requeridos[insumo.pk]} {insumo.unidad_medida}.")
    if faltantes:
        raise ValidationError({"insumos": ["Insumos insuficientes. " + " ".join(faltantes)]})
    return insumos


def reservar_insumos(pedido, cantidades):
    requeridos = calcular_receta(cantidades)
    bloquear_y_comprobar(requeridos)
    ReservaInsumo.objects.bulk_create([
        ReservaInsumo(pedido=pedido, insumo_id=insumo_id, cantidad=cantidad)
        for insumo_id, cantidad in requeridos.items()
    ])


def descontar_insumos(pedido):
    if pedido.reserva_registrada:
        reservas = list(pedido.reservas_insumos.filter(estado=ReservaInsumo.Estado.RESERVADA).order_by("insumo_id"))
        requeridos = {reserva.insumo_id: reserva.cantidad for reserva in reservas}
        # Las propias reservas ya pertenecen al pedido; solo se verifica el stock físico.
        insumos = bloquear_y_comprobar(requeridos, descontar_reservas=False)
        for reserva in reservas:
            reserva.estado = ReservaInsumo.Estado.CONSUMIDA
            reserva.save(update_fields=["estado"])
    else:
        # Pedidos anteriores: no se inventan reservas históricas. Se respetan las de otros pedidos.
        requeridos = calcular_receta(cantidades_por_producto(pedido.detalles.all()))
        insumos = bloquear_y_comprobar(requeridos)
    for insumo in insumos:
        insumo.cantidad_stock -= requeridos[insumo.pk]
        insumo.save(update_fields=["cantidad_stock"])
