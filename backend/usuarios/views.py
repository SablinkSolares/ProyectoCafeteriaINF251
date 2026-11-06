from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework import generics
from dinocafe.permissions import EsAdministrador
from django.contrib.auth import get_user_model

from .serializers import LoginSerializer, CuentaSerializer


class LoginView(TokenObtainPairView):
    serializer_class = LoginSerializer


class CuentaListCreateView(generics.ListCreateAPIView):
    permission_classes = [EsAdministrador]
    serializer_class = CuentaSerializer
    queryset = get_user_model().objects.order_by("username")
