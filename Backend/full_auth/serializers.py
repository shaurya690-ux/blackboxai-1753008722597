from djoser.serializers import UserSerializer as BaseUserSerializer, UserCreateSerializer as BaseCreateSerializer
from .models import CustomUser

class CustomUserSerializer(BaseUserSerializer):
    class Meta(BaseUserSerializer.Meta):
        model = CustomUser
        fields = ('id', 'username', 'email', 'role')  # include role in API output

class CustomUserCreateSerializer(BaseCreateSerializer):
    class Meta(BaseCreateSerializer.Meta):
        model = CustomUser
        fields = ('id', 'username', 'email', 'password')

    def create(self, validated_data):
        validated_data['role'] = 'student'  # Default role assigned on signup
        return super().create(validated_data)
