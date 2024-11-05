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


class TopSongs2023(APIView):
    def get(self, request, format=None):
        key = self.request.session.session_key

        # Define the target playlists from 2019 to 2023
        target_playlists = [
            "Your Top Songs 2023",
            "Your Top Songs 2022",
            "Your Top Songs 2021",
            "Your Top Songs 2020",
            "Your Top Songs 2019"
        ]

        # Fetch all user playlists
        endpoint = "me/playlists/"
        playlists_response = spotify_requests_execution(key, endpoint)

        if "error" in playlists_response:
            return Response({"error": "Failed to fetch playlists"}, status=status.HTTP_400_BAD_REQUEST)

        # Find any matching "Your Top Songs" playlists
        found_playlists = {}
        for playlist in playlists_response.get("items", []):
            playlist_name = playlist.get("name")
            if playlist_name in target_playlists:
                found_playlists[playlist_name] = playlist

        # If no matching playlists found, return an error
        if not found_playlists:
            return Response(
                {"error": "No 'Your Top Songs' playlists found from 2019 to 2023"},
                status=status.HTTP_404_NOT_FOUND
            )

        all_tracks = []

        # Retrieve and process tracks from each found playlist
        for playlist_name, playlist in found_playlists.items():
            playlist_id = playlist.get("id")
            tracks_endpoint = f"playlists/{playlist_id}/tracks/"
            tracks_response = spotify_requests_execution(key, tracks_endpoint)
            items = tracks_response.get("items", [])

            # Process each track
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
                        "popularity": track.get("popularity"),
                        "playlist_name": playlist_name  # Indicate which playlist the track came from
                    }
                    all_tracks.append(track_data)

        # Sort tracks by playlist year if desired, with the newest year first
        all_tracks.sort(key=lambda x: x["playlist_name"], reverse=True)

        # Response format
        playlist_info = {
            "combined_playlist_name": "Your Top Songs 2019-2023",
            "total_tracks": len(all_tracks),
            "tracks": all_tracks
        }

        return Response(playlist_info, status=status.HTTP_200_OK)