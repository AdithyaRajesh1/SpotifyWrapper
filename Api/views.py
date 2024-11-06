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
import sqlite3


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
        #return Response({"url": url}, status=status.HTTP_200_OK)
        return render(request, 'auth.html', {"url": url})


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
    redirect_url = f"http://localhost:8000/spotify/wrapped/?code={code}"
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


class TopSongs(APIView):
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

        playlists_by_year = {}

        # Retrieve and process tracks from each found playlist
        for playlist_name, playlist in found_playlists.items():
            playlist_id = playlist.get("id")
            tracks_endpoint = f"playlists/{playlist_id}/tracks/"
            tracks_response = spotify_requests_execution(key, tracks_endpoint)
            items = tracks_response.get("items", [])

            # Collect track data for the current playlist
            tracks = []
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
                    }
                    tracks.append(track_data)

            # Assign tracks to the playlist's year
            playlists_by_year[playlist_name] = tracks

        # Render to HTML with the playlist data
        return render(request, 'dashboard.html', {"playlists_by_year": playlists_by_year})


class SpotifyWrappedView(APIView):
    def get(self, request, format=None):
        key = self.request.session.session_key

        # Fetch top artists
        top_artists_endpoint = "me/top/artists?limit=5"
        top_artists_response = spotify_requests_execution(key, top_artists_endpoint)
        top_artists = [
            {
                "name": artist["name"],
                "genres": artist.get("genres", []),
                "image": artist["images"][0]["url"] if artist.get("images") else None
            }
            for artist in top_artists_response.get("items", [])
        ]

        # Fetch top tracks
        top_tracks_endpoint = "me/top/tracks?limit=5"
        top_tracks_response = spotify_requests_execution(key, top_tracks_endpoint)
        top_tracks = [
            {
                "name": track["name"],
                "artists": ", ".join([artist["name"] for artist in track["artists"]]),
                "album_cover": track["album"]["images"][0]["url"] if track["album"].get("images") else None
            }
            for track in top_tracks_response.get("items", [])
        ]

        # Aggregate genres from top artists
        genres = set()
        for artist in top_artists_response.get("items", []):
            genres.update(artist.get("genres", []))
        top_genres = list(genres)[:5]  # Limit to top 5 genres

        # Calculate listening time from playback history
        playback_history_endpoint = "me/player/recently-played?limit=50"
        playback_history_response = spotify_requests_execution(key, playback_history_endpoint)
        total_listening_time = sum(
            item["track"]["duration_ms"] for item in playback_history_response.get("items", [])
        )
        listening_time_hours = round(total_listening_time / (1000 * 60 * 60), 2)  # Convert ms to hours

        # Count new artists discovered
        new_artists = len({track["track"]["artists"][0]["id"] for track in playback_history_response.get("items", [])})

        # Mock data for other metrics
        music_trends = "Trending tracks of the year and global chart highlights"
        sound_town = "Your Sound Town: Nashville"
        listening_character = "The Adventurer - You explore a wide range of genres and discover new artists often."

        # Context for Wrapped data
        context = {
            "top_artists": top_artists,
            "top_tracks": top_tracks,
            "top_genres": top_genres,
            "listening_time_hours": listening_time_hours,
            "new_artists": new_artists,
            "music_trends": music_trends,
            "sound_town": sound_town,
            "listening_character": listening_character,
        }

        print("dablt")
        import sqlite3

        # Connect to the SQLite database
        conn = sqlite3.connect('db.sqlite3')  # Replace with the correct path if needed
        cursor = conn.cursor()

        # Get the list of all table names in the database
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()

        # Iterate through each table and display its contents
        for table in tables:
            table_name = table[0]
            print(f"Displaying data from table: {table_name}")

            try:
                # Query to select everything from the current table
                cursor.execute(f"SELECT * FROM {table_name}")

                # Fetch all rows from the table
                rows = cursor.fetchall()

                # If the table is empty, print a message
                if not rows:
                    print(f"Table {table_name} is empty.")
                else:
                    # Print each row in the table
                    for row in rows:
                        print(row)

            except sqlite3.Error as e:
                # Handle the case where a table can't be queried
                print(f"Error querying table {table_name}: {e}")

            print("\n" + "-" * 50 + "\n")

        # Close the connection when done
        conn.close()





        # Render the wrapped.html template with context
        return render(request, "wrapped.html", context)
