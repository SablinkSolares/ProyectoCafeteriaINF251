from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Usuario


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (("Rol en DinoCafé", {"fields": ("rol",)}),)
    list_display = ("username", "rol", "is_staff", "is_active")
    list_filter = ("rol", "is_staff", "is_active")
