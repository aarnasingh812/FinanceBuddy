from rest_framework import serializers
from django.contrib.auth.hashers import make_password
from models import User

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email')

class RegisterSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('username', 'email', 'password') 
        extra_kwargs = {
            'password': {'write_only': True}
        }
    def create(self, validated_data):
        # Hash the password manually
        validated_data['password'] = make_password(validated_data['password'])
        
        return User.objects.create(**validated_data)

class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)