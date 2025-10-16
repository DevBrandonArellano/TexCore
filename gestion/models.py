from django.db import models
from django.contrib.auth.models import AbstractUser

class Sede(models.Model):
    nombre = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.nombre

class Area(models.Model):
    nombre = models.CharField(max_length=100)
    sede = models.ForeignKey(Sede, on_delete=models.CASCADE, related_name='areas')

    def __str__(self):
        return f'{self.nombre} ({self.sede.nombre})'

class CustomUser(AbstractUser):
    # Django's AbstractUser already has:
    # username, first_name, last_name, email, password, is_active, etc.
    
    sede = models.ForeignKey(Sede, on_delete=models.SET_NULL, null=True, blank=True)
    area = models.ForeignKey(Area, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return self.username