from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import LoginView, PerfilView

urlpatterns = [
    path("me/", PerfilView.as_view(), name="perfil"),
    path("login/", LoginView.as_view(), name="login"),
    path("refresh/", TokenRefreshView.as_view(), name="token_refresh"),
]
