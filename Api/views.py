from django.shortcuts import render
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import response
from rest_framework import status
from requests import Request, post
from django.http import HttpResponseRedirect
from .models import Token

from .credentials import CLIENT_ID,CLIENT_SECRET,REDIRECT_URI
from .extras import create_or_update_tokens, is_spotify_authenticated, spotify_requests_execution


# Create your views here.

class Authentication(APIView):
    def get(self, request, format=None):
        scopes = ""
        url = Request('GET', 'https://accounts.spotify.com/authorize', params={
            'scope': scopes,
            'response_type': 'code',
            'redirect_uri': REDIRECT_URI,
            'client_id': CLIENT_ID,
            }).prepare().url
        return HttpResponseRedirect(url)
def spotify_redirect(request, format=None):
    code = request.GET.get('code')
    error = request.GET.get('error')

    if error:
        return error
    response = post("https://accounts.spotify.com/api/token", data = {
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': REDIRECT_URI,
        'client_id': CLIENT_ID,
    }).json()
    access_token = response.get('access_token')
    refresh_token = response.get('refresh_token')
    expires_in = response.get('expires_in')
    token_type = response.get('token_type')

    authKey = request.session.session_key
    if not request.session.exists(authKey):
        request.session.create()
        authKey = request.session.session_key

    create_or_update_tokens(
        sessionId=authKey,
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=expires_in,
        token_type=token_type,
    )

    redirect_url = f"http://127.0.0.1:8000/spotify/current-song?key={authKey}"
    return HttpResponseRedirect(redirect_url)

class CheckAuthentication(APIView):
    def get(self, request, format=None):
        key = self.request.session.session_key
        if not self.request.session.exists(key):
            self.request.session.create()
            key = self.request.session.session_key
        auth_status = is_spotify_authenticated(key)

        if auth_status:
            redirect_url = f"http://127.0.0.1:8000/spotify/current-song?key={key}"
            return HttpResponseRedirect(redirect_url)
        else:
            redirect_url = "http://127.0.0.1:8000/spotify/auth-url"
            return HttpResponseRedirect(redirect_url)
class CurrentSong(APIView):
    kwarg = "key"
    def get(self, request, format=None):
        key = request.GET.get(self.kwarg)
        token = Token.objects.get(user=key)
        print(token)

        endpoint = "player/currently-playing"
        response = spotify_requests_execution(key, endpoint)

        if "error" in response or "item" not in response:
            return Response({}, status = status.HTTP_204_NO_CONTENT)
        item = response.get("item")

        progress = response.get("progress")
        is_playing = response.get("is_playing")
        duration = item.get("duration")
        song_id = item.get("id")
        title = item.get("title")
        album_cover = item.get("album").get("images")[0].get("url")

        artists = ""
        for i,artist in enumerate(item.get("artists")):
            if i>0:
                artists += ", "
            name = artist.get("name")
            artists += name

        song = {
            "id": song_id,
            "title": title,
            "artists": artists,
            "duration": duration,
            "is_playing": is_playing,
            "album_cover": album_cover,
            "is_playing": is_playing,
        }

        print(song)
        return Response(song, status = status.HTTP_200_OK)