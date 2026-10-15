from rest_framework import serializers
from django.contrib.auth import authenticate
from .models import User

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'display_name', 'is_staff', 'is_superuser', 'is_active', 'created_at']
        read_only_fields = ['id', 'is_staff', 'is_superuser', 'is_active', 'created_at']

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ['id', 'email', 'password', 'display_name']

    def create(self, validated_data):
        return User.objects.create_user(
            email=validated_data['email'],
            password=validated_data['password'],
            display_name=validated_data.get('display_name', '')
        )

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        email = data.get('email', '').strip().lower()
        password = data.get('password')

        user_obj = User.objects.filter(email=email).first()
        if user_obj and user_obj.check_password(password):
            if not user_obj.is_active:
                raise serializers.ValidationError('This user account is inactive or suspended.')
            data['user'] = user_obj
            return data

        raise serializers.ValidationError('Invalid email or password.')
