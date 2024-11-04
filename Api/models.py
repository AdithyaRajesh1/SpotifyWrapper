from django.contrib.auth.models import User
from django.db import models

# Create your models here

class Token(models.Model):
    access_token = models.CharField(max_length=500)
    refresh_token = models.CharField(max_length=500)
    expires_in = models.DateTimeField()
    user = models.CharField(unique = True, max_length=50)
    token_type = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)

