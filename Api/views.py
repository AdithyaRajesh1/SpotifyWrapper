from django.shortcuts import render, redirect
from rest_framework.response import Response
from rest_framework.reverse import reverse_lazy
from rest_framework.views import APIView
from rest_framework import status
from requests import Request, post
from django.http import JsonResponse
from .models import Token
from .credentials import CLIENT_ID, CLIENT_SECRET, REDIRECT_URI
from .extras import create_or_update_tokens, is_spotify_authenticated, spotify_requests_execution


def home(request):
    return render(request, 'home.html')
class Authentication(APIView):
    def get(self, request, format=None):
        scopes = "user-read-currently-playing user-read-playback-state user-modify-playback-state user-top-read user-library-read playlist-read-private"
        url = Request('GET', 'https://accounts.spotify.com/authorize', params={
            'scope': scopes,
            'response_type': 'code',
            'redirect_uri': REDIRECT_URI,
            'client_id': CLIENT_ID,
        }).prepare().url
        return Response({"url": url}, status=status.HTTP_200_OK)


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
    }).json()


    print("Authorization Code:", code)

    if not request.session.exists(request.session.session_key):
        request.session.create()
        print('successful')

    access_token = response.get('access_token')
    refresh_token = response.get('refresh_token')
    expires_in = response.get('expires_in', 3600)
    token_type = response.get('token_type')
    error = response.get('error')

    create_or_update_tokens(
        session_id=request.session.session_key,
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=expires_in,
        token_type=token_type,
    )

    # Return redirect URL as JSON, handle on frontend
    redirect_url = f"http://localhost:8000/spotify/current-song/?code={code}"
    return redirect(redirect_url)


class CheckAuthentication(APIView):
    def get(self, request, format=None):
        is_authenticated = is_spotify_authenticated(self.request.session.session_key)
        return Response({"is_authenticated": is_authenticated}, status=status.HTTP_200_OK)

class CurrentSong(APIView):
    def get(self, request, format=None):
        key = self.request.session.session_key
        '''
        try:
            token = Token.objects.get(user=key)
        except Token.DoesNotExist:
            return Response({"error": "Token not found"}, status=status.HTTP_404_NOT_FOUND)
'''
        endpoint = "player/currently-playing"
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


class TopSongs2023(APIView):
    def get(self, request, format=None):
        key = self.request.session.session_key

        # First, get all playlists to find "Your Top Songs 2023"
        endpoint = "playlists/"
        playlists_response = spotify_requests_execution(key, endpoint)

        if "error" in playlists_response:
            return Response({"error": "Failed to fetch playlists"}, status=status.HTTP_400_BAD_REQUEST)

        # Find the "Your Top Songs 2023" playlist
        top_songs_playlist = None
        for playlist in playlists_response.get("items", []):
            if playlist.get("name") == "Your Top Songs 2023":
                top_songs_playlist = playlist
                break

        if not top_songs_playlist:
            return Response(
                {"error": "Your Top Songs 2023 playlist not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        # Get the tracks from the playlist
        playlist_id = top_songs_playlist.get("id")
        print(f"Found playlist ID: {playlist_id}")

        # Use the full endpoint path for Spotify-owned playlist
        tracks_endpoint = f"users/spotify/playlists/{playlist_id}/tracks"
        tracks_response = spotify_requests_execution(key, tracks_endpoint)

        if "error" in tracks_response:
            # Try alternative endpoint
            tracks_endpoint = f"playlists/{playlist_id}"
            tracks_response = spotify_requests_execution(key, tracks_endpoint)

            if "error" in tracks_response:
                return Response({
                    "error": "Failed to fetch tracks",
                    "playlist_id": playlist_id,
                    "response": tracks_response
                }, status=status.HTTP_400_BAD_REQUEST)

            # Get tracks from the tracks object
            tracks_response = tracks_response.get("tracks", {})

        tracks = []
        items = tracks_response.get("items", [])

        for item in items:
            track = item.get("track")
            if track:
                images = track.get("album", {}).get("images", [])
                album_cover = images[0].get("url") if images else None

                track_data = {
                    "id": track.get("id"),
                    "name": track.get("name"),
                    "artists": ", ".join(artist.get("name") for artist in track.get("artists", [])),
                    "album": track.get("album", {}).get("name"),
                    "album_cover": album_cover,
                    "duration_ms": track.get("duration_ms"),
                    "external_url": track.get("external_urls", {}).get("spotify"),
                    "preview_url": track.get("preview_url"),
                    "popularity": track.get("popularity")
                }
                tracks.append(track_data)

        playlist_info = {
            "playlist_name": top_songs_playlist.get("name"),
            "description": top_songs_playlist.get("description"),
            "owner": top_songs_playlist.get("owner", {}).get("display_name"),
            "total_tracks": len(tracks),
            "image_url": next((image.get("url") for image in top_songs_playlist.get("images", [])), None),
            "tracks": tracks
        }

        return Response(playlist_info, status=status.HTTP_200_OK)