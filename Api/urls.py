from django.contrib import admin
from django.urls import path, include
from Api.views import spotify_redirect, CheckAuthentication, CurrentSong

urlpatterns = [
    path('admin/', admin.site.urls),
    path('redirect', spotify_redirect),
    path('check-auth', CheckAuthentication.as_view()),
    path('current-song', CurrentSong.as_view()),
]