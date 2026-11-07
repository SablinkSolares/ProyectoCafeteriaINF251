"""Permisos reutilizables de la capa de negocio."""
from rest_framework.permissions import BasePermission


class EsAdministrador(BasePermission):
    """RD1: solo el administrador modifica el catálogo y los precios."""

    message = "Solo el administrador puede realizar esta operación."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.rol == "administrador"
        )
