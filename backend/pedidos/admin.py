from django.contrib import admin

from .models import DetallePedido, Pedido


class DetallePedidoInline(admin.TabularInline):
    model = DetallePedido
    extra = 0
    readonly_fields = ("producto", "cantidad", "precio_unitario", "preparable")
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = ("id", "mesa", "estado", "registrado_por", "creado_en", "total")
    list_filter = ("estado",)
    inlines = [DetallePedidoInline]
    readonly_fields = [f.name for f in Pedido._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
