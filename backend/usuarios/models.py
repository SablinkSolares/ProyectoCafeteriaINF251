from django.contrib.auth.models import AbstractUser
from django.db import models


class Usuario(AbstractUser):
    """Usuario del sistema con uno de los cuatro roles del negocio (RF10/RNF3)."""

    class Rol(models.TextChoices):
        ADMINISTRADOR = "administrador", "Administrador"
        MESERO = "mesero", "Mesero"
        CAJERO = "cajero", "Cajero"
        COCINA = "cocina", "Cocina"

    rol = models.CharField(
        max_length=20,
        choices=Rol.choices,
        default=Rol.MESERO,
        verbose_name="rol",
    )

    class Meta:
        verbose_name = "usuario"
        verbose_name_plural = "usuarios"

    def __str__(self):
        return f"{self.username} ({self.get_rol_display()})"
