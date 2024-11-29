from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views

from Api import views
from Api.views import spotify_redirect, CheckAuthentication, CurrentSong, Authentication, home, TopSongs, \
    SpotifyWrappedView, register, GameView, delete_account, PostListView
urlpatterns = [

    path('', home, name='home'),
    path('admin/', admin.site.urls),
    path('redirect/', spotify_redirect, name='redirect'),
    path('check-auth/', Authentication.as_view(), name='check-auth'),
    path('current-song/', CurrentSong.as_view()),
    path('top/', TopSongs.as_view()),
    path('wrapped/', SpotifyWrappedView.as_view(), name = 'wrapped'),
    path('game/', GameView.as_view(), name='game'),


    path('register/',register, name='register'),
    path('login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    path('password_reset/', auth_views.PasswordResetView.as_view(template_name='password_reset.html'), name='password_reset'),
    path('password_reset_done/', auth_views.PasswordResetDoneView.as_view(template_name='password_reset_done.html'), name='password_reset_done'),
    path('password_reset_confirm/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='password_reset_confirm.html'), name='password_reset_confirm'),
    path('password_reset_complete/', auth_views.PasswordResetCompleteView.as_view(template_name='password_reset_complete.html'), name='password_reset_complete'),
    path('delete-account/', delete_account, name='delete_account'),

    path('wrapped/intro/', views.SpotifyWrappedOverviewView.as_view(), name='wrapped_intro'),
    path('wrapped/artists/', views.SpotifyWrappedArtistsView.as_view(), name='wrapped_artists'),
    path('wrapped/tracks/', views.SpotifyWrappedTracksView.as_view(), name='wrapped_tracks'),
    path('wrapped/albums/', views.SpotifyWrappedAlbumsView.as_view(), name='wrapped_albums'),
    path('wrapped/profile/', views.SpotifyWrappedProfileView.as_view(), name='wrapped_profile'),
    path('wrapped/response/', views.SpotifyWrappedGenAIView.as_view(), name='wrapped_response'),

    path('wrapped/genres', views.TopGenresView.as_view(), name='wrapped_genres'),

    path('wrapped/locations', views.TopLocationsView.as_view(), name='wrapped_locations'),

    path('savedwraps/', views.savedwraps, name='savedwraps'),
    path('wrap/<int:id>/', views.wrap_detail, name='wrap_detail'),  # Detailed view for each wrap
    path('post-wrap/<int:wrap_id>/', views.post_wrap_to_website, name='post_wrap_to_website'),
    #path('posts/', views.PostListView.as_view(), name='post_list'),
path('posts/', views.PostListView.as_view(), name='post_list'),

    path('savedwraps/artists/<int:id>/', views.saved_spotify_wrapped_artists, name='saved_spotify_wrapped_artists'),
    path('savedwraps/tracks/<int:id>/', views.saved_spotify_wrapped_tracks, name='saved_spotify_wrapped_tracks'),
    path('savedwraps/albums/<int:id>/', views.saved_spotify_wrapped_albums, name='saved_spotify_wrapped_albums'),
    path('savedwraps/profile/<int:id>/', views.saved_spotify_wrapped_profile, name='saved_spotify_wrapped_profile'),

    path('wrap/<int:id>/', views.wrap_detail, name='wrap_detail'),

    path('delete_wrap/<int:id>/', views.delete_spotify_wrap, name='delete_spotify_wrap'),
    path('posted-wraps/', views.WebsiteSocial, name='post_list'),
    path('delete_social/<int:id>/', views.delete_social, name='delete_social'),
    path('contact/', views.contact_developers, name='contact_developers'),
]
# Detailed view for each wrap
