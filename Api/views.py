from django.shortcuts import render
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from requests import Request, post
from django.http import JsonResponse
from .models import Token
from .credentials import CLIENT_ID, CLIENT_SECRET, REDIRECT_URI
from .extras import create_or_update_tokens, is_spotify_authenticated, spotify_requests_execution

class Authentication(APIView):
    def get(self, request, format=None):
        scopes = "user-read-currently-playing user-read-playback-state user-modify-playback-state"
        url = Request('GET', 'https://accounts.spotify.com/authorize', params={
            'scope': scopes,
            'response_type': 'code',
            'redirect_uri': REDIRECT_URI,
            'client_id': CLIENT_ID,
        }).prepare().url
        return Response({"auth_url": url}, status=status.HTTP_200_OK)

#hello
def spotify_redirect(request):
    code = request.GET.get('code')
    error = request.GET.get('error')

    if error:
        return JsonResponse({"error": error}, status=status.HTTP_400_BAD_REQUEST)

    response = post(
    'https://accounts.spotify.com/api/token',
    data={
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': REDIRECT_URI,
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
    },
    headers={'Content-Type': 'application/x-www-form-urlencoded'}
    ).json()

    print("Authorization Code:", code)
    print("Spotify Response:", response.status_code, response.json())

    access_token = response.get('access_token')
    refresh_token = response.get('refresh_token')
    expires_in = response.get('expires_in', 3600)
    token_type = response.get('token_type')

    if not access_token or not refresh_token or not expires_in:
        return JsonResponse({"error": "Invalid response from Spotify"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    auth_key = request.session.session_key
    if not request.session.exists(auth_key):
        request.session.create()
        auth_key = request.session.session_key

    create_or_update_tokens(
        session_id=auth_key,
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=expires_in,
        token_type=token_type,
    )

    # Return redirect URL as JSON, handle on frontend
    redirect_url = f"http://127.0.0.1:8000/spotify/current-song?key={auth_key}"
    return JsonResponse({"redirect_url": redirect_url}, status=status.HTTP_200_OK)


class CheckAuthentication(APIView):
    def get(self, request, format=None):
        key = self.request.session.session_key
        if not self.request.session.exists(key):
            self.request.session.create()
            key = self.request.session.session_key
        auth_status = is_spotify_authenticated(key)

        if auth_status:
            redirect_url = f"http://127.0.0.1:8000/spotify/current-song?key={key}"
        else:
            redirect_url = "http://127.0.0.1:8000/spotify/redirect"

        return Response({"redirect": redirect_url}, status=status.HTTP_200_OK)


class CurrentSong(APIView):
    def get(self, request, format=None):
        key = request.GET.get("key")
        try:
            token = Token.objects.get(user=key)
        except Token.DoesNotExist:
            return Response({"error": "Token not found"}, status=status.HTTP_404_NOT_FOUND)

        endpoint = "me/player/currently-playing"
        response = spotify_requests_execution(key, endpoint)

        if "error" in response or "item" not in response:
            return Response({}, status=status.HTTP_204_NO_CONTENT)

        item = response.get("item")
        progress = response.get("progress_ms")
        is_playing = response.get("is_playing")
        duration = item.get("duration_ms")
        song_id = item.get("id")
        title = item.get("name")
        album_cover = item.get("album", {}).get("images", [{}])[0].get("url")
        artists = ", ".join(artist.get("name") for artist in item.get("artists", []))

        song = {
            "id": song_id,
            "title": title,
            "artists": artists,
            "duration": duration,
            "is_playing": is_playing,
            "album_cover": album_cover,
            "progress": progress,
        }

        return Response(song, status=status.HTTP_200_OK)
