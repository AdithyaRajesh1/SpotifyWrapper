from django.contrib.auth.models import User
from django.db import models

# Create your models here

class Token(models.Model):
    access_token = models.CharField(max_length=500)
    refresh_token = models.CharField(max_length=500)
    expires_in = models.DateTimeField()
    user = models.CharField(max_length=50, unique=True)
    token_type = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)


from django.db import models
from django.contrib.auth.models import User

from django.db import models

from django.db import models
from django.contrib.auth.models import User

class SpotifyWrapped(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='spotify_wraps')
    time_range = models.CharField(max_length=20)  # e.g., 'short_term', 'medium_term', 'long_term'
    total_artists = models.IntegerField()
    total_tracks = models.IntegerField()
    total_albums = models.IntegerField()
    total_locations = models.IntegerField()
    new_artists_count = models.IntegerField()
    listening_time_hours = models.FloatField()
    top_genres = models.JSONField()  # Store genres as a list of dictionaries
    top_artists = models.JSONField()  # Store artists as a list of dictionaries
    top_tracks = models.JSONField()  # Store tracks as a list of dictionaries
    top_albums = models.JSONField()  # Store albums as a list of dictionaries
    top_locations = models.JSONField()  # Store locations as a list of dictionaries
    user_profile = models.JSONField()  # Store user profile details
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.time_range} Wrapped"






