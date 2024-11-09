from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from Api.views import spotify_redirect, CheckAuthentication, CurrentSong, Authentication, home, TopSongs, \
    SpotifyWrappedView, register



urlpatterns = [

    path('', home, name='home'),
    path('admin/', admin.site.urls),
    path('redirect/', spotify_redirect, name='redirect'),
    path('check-auth/', Authentication.as_view(), name='check-auth'),
    path('current-song/', CurrentSong.as_view()),
    path('top/', TopSongs.as_view()),
    path('wrapped/', SpotifyWrappedView.as_view()),


    path('register/',register, name='register'),
    path('login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    path('password_reset/', auth_views.PasswordResetView.as_view(template_name='password_reset.html'), name='password_reset'),
    path('password_reset_done/', auth_views.PasswordResetDoneView.as_view(template_name='password_reset_done.html'), name='password_reset_done'),
    path('password_reset_confirm/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='password_reset_confirm.html'), name='password_reset_confirm'),
    path('password_reset_complete/', auth_views.PasswordResetCompleteView.as_view(template_name='password_reset_complete.html'), name='password_reset_complete'),
]
