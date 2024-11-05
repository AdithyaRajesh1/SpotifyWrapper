from django.contrib import admin
from django.urls import path, include
from Api.views import spotify_redirect, CheckAuthentication, CurrentSong, Authentication, home, TopSongs2023

urlpatterns = [

    path('', home, name='home'),
    path('admin/', admin.site.urls),
    path('redirect/', spotify_redirect, name='redirect'),
    path('check-auth/', Authentication.as_view(), name='check-auth'),
    path('current-song/', CurrentSong.as_view()),
    path('wrapped/', TopSongs2023.as_view())
]