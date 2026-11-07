from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework import serializers
from django.contrib.auth import get_user_model


Usuario = get_user_model()


class CuentaSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8, max_length=128, trim_whitespace=False)
    rol = serializers.ChoiceField(choices=Usuario.Rol.choices, required=True)

    class Meta:
        model = Usuario
        fields = ["id", "username", "first_name", "last_name", "email", "rol", "is_active", "password"]
        read_only_fields = ["id", "is_active"]

    def create(self, validated_data):
        # create_user aplica el hash de Django y no concede permisos del admin de Django.
        return Usuario.objects.create_user(**validated_data)


class LoginSerializer(TokenObtainPairSerializer):
    """Añade el rol al token y a la respuesta para que React lo guarde."""

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["rol"] = user.rol
        token["username"] = user.username
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        data["rol"] = self.user.rol
        data["username"] = self.user.username
        return data
