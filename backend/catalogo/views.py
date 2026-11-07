
from decimal import Decimal, InvalidOperation

from django.db.models import Q

from rest_framework import viewsets
from rest_framework.permissions import AllowAny, IsAuthenticated, SAFE_METHODS
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.pagination import PageNumberPagination

from dinocafe.permissions import EsAdministrador

from .models import Categoria, Producto, Insumo, ConfiguracionPago
from .serializers import CategoriaSerializer, ProductoSerializer, InsumoSerializer, ProductoMenuSerializer, ActualizarStockSerializer
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.core.files.storage import default_storage
from rest_framework import serializers
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser
from rest_framework.exceptions import PermissionDenied
import uuid


class ProductoPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100


class MenuPublicoView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        productos = Producto.objects.filter(activo=True).select_related("categoria")
        categorias = Categoria.objects.filter(productos__activo=True).distinct()
        return Response({
            "categorias": [{"id": categoria.pk, "nombre": categoria.nombre} for categoria in categorias],
            "productos": ProductoMenuSerializer(productos, many=True).data,
        })


class CategoriaViewSet(viewsets.ReadOnlyModelViewSet):
    """GET /api/categorias/."""

    queryset = Categoria.objects.all()
    serializer_class = CategoriaSerializer
    permission_classes = [IsAuthenticated]
    lookup_value_converter = "int"


class ProductoViewSet(viewsets.ModelViewSet):
    """Catálogo con búsqueda y filtros optimizados."""

    serializer_class = ProductoSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = ProductoPagination
    lookup_value_converter = "int"

    def get_permissions(self):
        if self.request.method in SAFE_METHODS:
            return [IsAuthenticated()]
        return [EsAdministrador()]

    def get_queryset(self):

        qs = Producto.objects.select_related("categoria", "existencia").prefetch_related("insumos__insumo")
        activo = self.request.query_params.get("activo", "").strip().lower()
        if self.request.user.rol != "administrador":
            qs = qs.filter(activo=True)
        elif activo:
            if activo not in {"true", "false"}:
                raise ValidationError({"activo": "Usa true o false."})
            qs = qs.filter(activo=activo == "true")

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

    def perform_destroy(self, instance):
        instance.activo = False
        instance.save(update_fields=["activo", "actualizado_en"])

    @transaction.atomic
    @action(detail=True, methods=["patch"], url_path="stock")
    def actualizar_stock(self, request, pk=None):
        entrada = ActualizarStockSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        producto = get_object_or_404(Producto.objects.select_for_update(), pk=pk)
        if producto.preparable:
            raise ValidationError({"stock": "La disponibilidad de este producto se calcula con sus insumos. Actualízalos desde Inventario."})
        anterior = entrada.validated_data.get("stock_anterior")
        if anterior is not None and producto.stock != anterior:
            return Response({"detail": "El stock cambió mientras lo editabas. Actualiza el catálogo y vuelve a intentarlo."}, status=409)
        producto.stock = entrada.validated_data["stock"]
        producto.save(update_fields=["stock", "actualizado_en"])
        return Response(self.get_serializer(producto).data)


class InsumoViewSet(viewsets.ModelViewSet):
    queryset = Insumo.objects.order_by("nombre_insumo")
    serializer_class = InsumoSerializer
    permission_classes = [EsAdministrador]
    lookup_value_converter = "int"
    http_method_names = ["get", "post", "patch", "head", "options"]

    @transaction.atomic
    def partial_update(self, request, *args, **kwargs):
        self.kwargs["pk"] = kwargs["pk"]
        instance = get_object_or_404(self.get_queryset().select_for_update(), pk=kwargs["pk"])
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class SubirImagenView(APIView):
    permission_classes = [EsAdministrador]
    parser_classes = [MultiPartParser]

    def post(self, request):
        class ImagenSerializer(serializers.Serializer):
            imagen = serializers.ImageField()
        entrada = ImagenSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        archivo = entrada.validated_data["imagen"]
        if archivo.size > 5 * 1024 * 1024:
            raise ValidationError({"imagen": "La imagen no debe superar 5 MB."})
        formato = archivo.image.format.lower()
        if formato not in {"png", "jpeg", "webp"}:
            raise ValidationError({"imagen": "Usa PNG, JPEG o WebP."})
        nombre = default_storage.save(f"productos/{uuid.uuid4().hex}.{formato}", archivo)
        return Response({"imagen": default_storage.url(nombre)}, status=201)


class ConfiguracionPagoSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConfiguracionPago
        fields = ["qr_habilitado", "imagen_qr"]

    def validate_imagen_qr(self, value):
        if value and not value.startswith(("/media/", "/images/", "https://", "http://")):
            raise ValidationError("Usa una imagen subida o una URL HTTP(S).")
        return value


class ConfiguracionPagoView(APIView):
    def get(self, request):
        objeto, _ = ConfiguracionPago.objects.get_or_create(pk=1)
        return Response(ConfiguracionPagoSerializer(objeto).data)

    def patch(self, request):
        if request.user.rol != "administrador":
            raise PermissionDenied("Solo administración configura el QR.")
        objeto, _ = ConfiguracionPago.objects.get_or_create(pk=1)
        serializer = ConfiguracionPagoSerializer(objeto, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

