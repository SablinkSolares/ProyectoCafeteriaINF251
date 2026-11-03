from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated, SAFE_METHODS

from dinocafe.permissions import EsAdministrador

from .models import Categoria, Producto
from .serializers import CategoriaSerializer, ProductoSerializer


class CategoriaViewSet(viewsets.ReadOnlyModelViewSet):
    """GET /api/categorias/ (consulta para el catálogo)."""

    queryset = Categoria.objects.all()
    serializer_class = CategoriaSerializer
    permission_classes = [IsAuthenticated]


class ProductoViewSet(viewsets.ModelViewSet):
    """Catálogo: lectura para todos los roles, escritura solo del administrador (RD1)."""

    serializer_class = ProductoSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.request.method in SAFE_METHODS:
            return [IsAuthenticated()]
        return [EsAdministrador()]

    def get_queryset(self):
        qs = Producto.objects.select_related("categoria")
        q = self.request.query_params.get("q", "").strip()
        categoria = self.request.query_params.get("categoria", "").strip()
        if q:
            qs = qs.filter(nombre__icontains=q)  # RF9: coincidencia ILIKE
        if categoria:
            qs = qs.filter(categoria_id=categoria)
        return qs
