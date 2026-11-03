from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response


@api_view(["GET"])
@permission_classes([AllowAny])
def health(request):
    """Comprobación simple para saber si el backend de prueba está arriba."""
    return Response({"status": "ok", "servicio": "dinocafe-backend"})
