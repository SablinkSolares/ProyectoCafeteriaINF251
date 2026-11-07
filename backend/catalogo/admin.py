from django.contrib import admin
from django import forms
from django.db.models import Sum

from .models import Categoria, Insumo, Producto, ProductoInsumo


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ("id", "nombre")
    search_fields = ("nombre",)


class ProductoInsumoInline(admin.TabularInline):
    model = ProductoInsumo
    extra = 1


@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ("id", "nombre", "categoria", "precio", "stock")
    list_filter = ("categoria",)
    search_fields = ("nombre",)
    inlines = (ProductoInsumoInline,)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class InsumoAdminForm(forms.ModelForm):
    class Meta:
        model = Insumo
        fields = "__all__"

    def clean_cantidad_stock(self):
        cantidad = self.cleaned_data["cantidad_stock"]
        if self.instance.pk:
            from pedidos.models import ReservaInsumo
            # El admin ejecuta la edición en una transacción; el bloqueo impide
            # cambios de inventario simultáneos a la creación de reservas.
            Insumo.objects.select_for_update().get(pk=self.instance.pk)
            reservado = ReservaInsumo.objects.filter(
                insumo_id=self.instance.pk, estado=ReservaInsumo.Estado.RESERVADA
            ).aggregate(total=Sum("cantidad"))["total"] or 0
            if cantidad < reservado:
                raise forms.ValidationError(f"Hay {reservado} unidades reservadas en pedidos; el stock no puede ser menor.")
        return cantidad


@admin.register(Insumo)
class InsumoAdmin(admin.ModelAdmin):
    form = InsumoAdminForm
    list_display = ("id", "nombre_insumo", "unidad_medida", "cantidad_stock")
    search_fields = ("nombre_insumo",)
