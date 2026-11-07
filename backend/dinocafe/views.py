from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.db import connection, DatabaseError


@api_view(["GET"])
@permission_classes([AllowAny])
def health(request):
    """Comprobación simple para saber si el backend de prueba está arriba."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except DatabaseError:
        return Response({"status": "error", "servicio": "dinocafe-backend"}, status=503)
    return Response({"status": "ok", "servicio": "dinocafe-backend"})
