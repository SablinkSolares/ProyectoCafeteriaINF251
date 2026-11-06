from django.db import IntegrityError, transaction
from django.test import TestCase

from .models import Pago, Pedido, Reembolso


class ReembolsoModeloTests(TestCase):
    def test_un_solo_reembolso_por_pago(self):
        pedido = Pedido.objects.create()
        pago = Pago.objects.create(pedido=pedido, monto="7.00", metodo=Pago.Metodo.EFECTIVO)
        Reembolso.objects.create(pago=pago, importe_reembolsado="7.00")
        with self.assertRaises(IntegrityError), transaction.atomic():
            Reembolso.objects.create(pago=pago, importe_reembolsado="7.00")
