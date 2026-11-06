
from decimal import Decimal, InvalidOperation

from django.db.models import Q

from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated, SAFE_METHODS
from rest_framework.exceptions import ValidationError
from rest_framework.pagination import PageNumberPagination

from dinocafe.permissions import EsAdministrador

from .models import Categoria, Producto
from .serializers import CategoriaSerializer, ProductoSerializer


class ProductoPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100


class CategoriaViewSet(viewsets.ReadOnlyModelViewSet):
    """GET /api/categorias/."""

    queryset = Categoria.objects.all()
    serializer_class = CategoriaSerializer
    permission_classes = [IsAuthenticated]


class ProductoViewSet(viewsets.ModelViewSet):
    """Catálogo con búsqueda y filtros optimizados."""

    serializer_class = ProductoSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = ProductoPagination

    def get_permissions(self):
        if self.request.method in SAFE_METHODS:
            return [IsAuthenticated()]
        return [EsAdministrador()]

    def get_queryset(self):

        qs = Producto.objects.select_related("categoria", "existencia")

        # Búsqueda parcial por nombre.
        q = self.request.query_params.get("q", "").strip()

        if len(q) > 120:
            raise ValidationError({
                "q": "La búsqueda no puede superar 120 caracteres."
            })

        if q:
            qs = qs.filter(nombre__icontains=q)

        # Filtro por categoría.
        categoria = self.request.query_params.get(
            "categoria", ""
        ).strip()

        if categoria:
            if not categoria.isdigit():
                raise ValidationError({
                    "categoria": "Debes proporcionar un ID válido."
                })

            qs = qs.filter(categoria_id=int(categoria))

        # Filtro por precio mínimo.
        precio_min = self.obtener_precio("precio_min")

        if precio_min is not None:
            qs = qs.filter(precio__gte=precio_min)

        # Filtro por precio máximo.
        precio_max = self.obtener_precio("precio_max")

        if precio_max is not None:
            qs = qs.filter(precio__lte=precio_max)

        if (
            precio_min is not None
            and precio_max is not None
            and precio_min > precio_max
        ):
            raise ValidationError({
                "precio": "El precio mínimo no puede superar al máximo."
            })

        # Filtro de disponibilidad.
        disponible = self.request.query_params.get("disponible")

        if disponible is not None:

            disponible = disponible.lower().strip()

            if disponible not in {"true", "false"}:
                raise ValidationError({
                    "disponible": "Utiliza true o false."
                })

            if disponible == "true":
                qs = qs.filter(existencia__cantidad_stock__gt=0)
            else:
                qs = qs.filter(existencia__cantidad_stock=0)

        # Ordenamiento permitido.
        ordering = self.request.query_params.get(
            "ordering", "nombre"
        ).strip()

        campos_permitidos = {
            "nombre",
            "-nombre",
            "precio",
            "-precio",
            "stock",
            "-stock",
        }

        if ordering not in campos_permitidos:
            raise ValidationError({
                "ordering": (
                    "Ordenamiento no válido. Usa nombre, -nombre, "
                    "precio, -precio, stock o -stock."
                )
            })

        orden_db = {"stock": "existencia__cantidad_stock", "-stock": "-existencia__cantidad_stock"}
        return qs.order_by(orden_db.get(ordering, ordering), "id")

    def obtener_precio(self, parametro):

        valor = self.request.query_params.get(parametro)

        if valor is None or valor.strip() == "":
            return None

        try:
            precio = Decimal(valor)

        except (InvalidOperation, ValueError):
            raise ValidationError({
                parametro: "Introduce un precio decimal válido."
            })

        if not precio.is_finite() or precio < 0:
            raise ValidationError({
                parametro: "El precio debe ser un número positivo."
            })

        if precio.as_tuple().exponent < -2:
            raise ValidationError({
                parametro: "El precio admite máximo dos decimales."
            })

        return precio

