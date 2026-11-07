from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework import generics
from dinocafe.permissions import EsAdministrador
from django.contrib.auth import get_user_model

from .serializers import LoginSerializer, CuentaSerializer
from rest_framework.views import APIView
from rest_framework.response import Response


class LoginView(TokenObtainPairView):
    serializer_class = LoginSerializer


class PerfilView(APIView):
    def get(self, request):
        return Response({"id": request.user.pk, "username": request.user.username, "rol": request.user.rol})


class CuentaListCreateView(generics.ListCreateAPIView):
    permission_classes = [EsAdministrador]
    serializer_class = CuentaSerializer
    queryset = get_user_model().objects.order_by("username")
