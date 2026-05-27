"""Serializers para la API interna. ISP: un serializer por caso de uso."""
from rest_framework import serializers


class ServiceTokenRequestSerializer(serializers.Serializer):
    service_name = serializers.CharField(max_length=100)
    service_secret = serializers.CharField(max_length=500)


class ServiceTokenRefreshRequestSerializer(serializers.Serializer):
    refresh_token = serializers.CharField()
