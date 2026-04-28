# backend/api/serializers.py
from rest_framework import serializers
from django.contrib.auth.models import User
from .models import UserMedia

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email']
        read_only_fields = ['id']

class UserMediaSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserMedia
        fields = '__all__'
        read_only_fields = ['user', 'objects_detected', 'tags', 'faces_detected', 'labels']