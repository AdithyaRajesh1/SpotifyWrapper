from django.contrib.auth.decorators import login_required
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
from collections import Counter
from datetime import datetime, timedelta
import sqlite3
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from rest_framework.permissions import IsAuthenticated
from django.core.serializers.json import DjangoJSONEncoder
import urllib.parse





def home(request):
    if request.user.is_authenticated:
        return redirect('spotify/check-auth')  # Replace 'dashboard' with your dashboard route name
    else:
        return redirect('login')  # Replace 'login' with your login route name




def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Account created successfully. Please log in.')
            return redirect('login')
    else:
        form = UserCreationForm()
    return render(request, 'register.html', {'form': form})

class Authentication(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request, format=None):
        scopes = "user-read-currently-playing user-read-playback-state user-modify-playback-state user-top-read user-library-read playlist-read-private user-read-recently-played user-read-private user-read-email"
        url = Request('GET', 'https://accounts.spotify.com/authorize', params={
            'scope': scopes,
            'response_type': 'code',
            'redirect_uri': REDIRECT_URI,
            'client_id': CLIENT_ID,
        }).prepare().url
        #return Response({"url": url}, status=status.HTTP_200_OK)
        return render(request, 'auth.html', {"url": url})




@login_required
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
    permission_classes = [IsAuthenticated]
    def get(self, request, format=None):
        is_authenticated = is_spotify_authenticated(self.request.session.session_key)
        return Response({"is_authenticated": is_authenticated}, status=status.HTTP_200_OK)

class CurrentSong(APIView):
    permission_classes = [IsAuthenticated]
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
    permission_classes = [IsAuthenticated]
    def get(self, request, format=None):
        key = self.request.session.session_key
        target_playlists = [
            "Your Top Songs 2023",
            "Your Top Songs 2022",
            "Your Top Songs 2021",
            "Your Top Songs 2020",
            "Your Top Songs 2019"
        ]

        endpoint = "me/playlists/"
        playlists_response = spotify_requests_execution(key, endpoint)

        if "error" in playlists_response:
            return Response({"error": "Failed to fetch playlists"}, status=status.HTTP_400_BAD_REQUEST)

        found_playlists = {}
        for playlist in playlists_response.get("items", []):
            playlist_name = playlist.get("name")
            if playlist_name in target_playlists:
                found_playlists[playlist_name] = playlist

        playlists_by_year = {}

        for playlist_name, playlist in found_playlists.items():
            playlist_id = playlist.get("id")
            tracks_endpoint = f"playlists/{playlist_id}/tracks/"
            tracks_response = spotify_requests_execution(key, tracks_endpoint)
            items = tracks_response.get("items", [])

            tracks = []
            for item in items:
                track = item.get("track")
                if track:
                    track_data = {
                        "id": track.get("id"),
                        "name": track.get("name"),
                        "artists": ", ".join(artist.get("name") for artist in track.get("artists", [])),
                        "album": track.get("album", {}).get("name"),
                        "album_cover": track.get("album", {}).get("images", [{}])[0].get("url"),
                        "duration_ms": track.get("duration_ms"),
                        "preview_url": track.get("preview_url"),  # Add preview URL for playback
                        "popularity": track.get("popularity"),
                    }
                    tracks.append(track_data)
            playlists_by_year[playlist_name] = tracks

        return render(request, 'dashboard.html', {"playlists_by_year": playlists_by_year})


class SpotifyWrappedView(APIView):
    def get(self, request, format=None):
        key = self.request.session.session_key

        # Get time range from query parameters, default to medium_term
        time_range = request.GET.get('time_range', 'medium_term')

        # Validate time range
        valid_ranges = ['short_term', 'medium_term', 'long_term']
        if time_range not in valid_ranges:
            time_range = 'medium_term'

        # Fetch all necessary data from Spotify API with selected time range
        # 1. Top Artists
        top_artists_endpoint = f"me/top/artists?time_range={time_range}&limit=50"
        top_artists_response = spotify_requests_execution(key, top_artists_endpoint)

        # 2. Top Tracks
        top_tracks_endpoint = f"me/top/tracks?time_range={time_range}&limit=50"
        top_tracks_response = spotify_requests_execution(key, top_tracks_endpoint)

        # 3. Recently played tracks (this endpoint doesn't use time_range)
        recent_tracks_endpoint = "me/player/recently-played?limit=50"
        recent_tracks_response = spotify_requests_execution(key, recent_tracks_endpoint)

        # 4. Get user's playlists
        playlists_endpoint = "me/playlists"
        playlists_response = spotify_requests_execution(key, playlists_endpoint)

        # 5. Get user profile
        profile_endpoint = "me"
        profile_response = spotify_requests_execution(key, profile_endpoint)

        # Process the data
        all_artists = set()
        for artist in top_artists_response.get("items", []):
            all_artists.add(artist["id"])

        for track in top_tracks_response.get("items", []):
            for artist in track["artists"]:
                all_artists.add(artist["id"])

        # Calculate new artists discovered
        recent_artists = set()
        for item in recent_tracks_response.get("items", []):
            for artist in item["track"]["artists"]:
                recent_artists.add(artist["id"])

        new_artists = recent_artists - all_artists

        # Track-related metrics
        all_tracks = set(track["id"] for track in top_tracks_response.get("items", []))

        # Album-related metrics
        all_albums = set(track["album"]["id"] for track in top_tracks_response.get("items", []))

        # Location/Market metrics
        all_markets = set()
        for track in top_tracks_response.get("items", []):
            all_markets.update(track.get("available_markets", []))

        # Calculate listening time
        total_listening_time = sum(
            item["track"]["duration_ms"]
            for item in recent_tracks_response.get("items", [])
        )
        listening_time_hours = round(total_listening_time / (1000 * 60 * 60), 2)

        # Process top genres
        genres = []
        for artist in top_artists_response.get("items", []):
            genres.extend(artist.get("genres", []))
        top_genres = Counter(genres).most_common(5)

        # Time range display names
        time_range_display = {
            'short_term': 'Last 4 Weeks',
            'medium_term': 'Last 6 Months',
            'long_term': 'All Time'
        }

        # Structure the data for the frontend
        wrapped_data = {
            # Time range information
            "currentTimeRange": time_range,
            "timeRangeDisplay": time_range_display[time_range],
            "availableTimeRanges": [
                {'value': tr, 'display': time_range_display[tr]}
                for tr in valid_ranges
            ],

            # Total counts
            "totalArtists": len(all_artists),
            "totalTracks": len(all_tracks),
            "totalAlbums": len(all_albums),
            "totalLocations": len(all_markets),
            "newArtistsCount": len(new_artists),

            # Listening statistics
            "listeningTimeHours": listening_time_hours,
            "topGenres": [{"name": genre, "count": count} for genre, count in top_genres],

            # Top Artists
            "topArtists": [
                {
                    "name": artist["name"],
                    "subtitle": ", ".join(artist.get("genres", [])[:2]),
                    "image": artist["images"][0]["url"] if artist.get("images") else None,
                    "popularity": artist.get("popularity", 0),
                    "genres": artist.get("genres", []),
                    "spotifyUrl": artist["external_urls"]["spotify"]
                }
                for artist in top_artists_response.get("items", [])[:5]
            ],

            # Top Tracks
            "topTracks": [
                {
                    "name": track["name"],
                    "subtitle": ", ".join(artist["name"] for artist in track["artists"]),
                    "image": track["album"]["images"][0]["url"] if track["album"].get("images") else None,
                    "popularity": track.get("popularity", 0),
                    "previewUrl": track.get("preview_url"),
                    "spotifyUrl": track["external_urls"]["spotify"],
                    "albumName": track["album"]["name"],
                    "duration": track["duration_ms"]
                }
                for track in top_tracks_response.get("items", [])[:5]
            ],

            # Top Albums (unchanged)
            "topAlbums": [
                {
                    "name": track["album"]["name"],
                    "subtitle": track["album"]["artists"][0]["name"],
                    "image": track["album"]["images"][0]["url"] if track["album"].get("images") else None,
                    "releaseDate": track["album"].get("release_date"),
                    "totalTracks": track["album"].get("total_tracks"),
                    "spotifyUrl": track["album"]["external_urls"]["spotify"]
                }
                for track in top_tracks_response.get("items", [])[:5]
            ],

            # Top Locations
            "topLocations": [
                {
                    "name": market,
                    "count": len([
                        track for track in top_tracks_response.get("items", [])
                        if market in track.get("available_markets", [])
                    ])
                }
                for market in list(all_markets)[:5]
            ],

            # User Profile
            "userProfile": {
                "name": profile_response.get("display_name"),
                "image": profile_response.get("images", [{}])[0].get("url") if profile_response.get("images") else None,
                "country": profile_response.get("country"),
                "product": profile_response.get("product"),
                "followersCount": profile_response.get("followers", {}).get("total", 0)
            }
        }

        wrapped_data['sharing'] = self.generate_sharing_data(wrapped_data, request)

        # Return JSON for API consumption
        if request.headers.get('Accept') == 'application/json':
            return JsonResponse(wrapped_data, encoder=DjangoJSONEncoder)

        # Otherwise render the template
        return render(request, "wrapped.html", {
            "wrapped_data": wrapped_data,
            "page_title": f"Your Spotify Wrapped - {time_range_display[time_range]}",
            "current_year": datetime.now().year,
            "request": request  # Pass request to template for building absolute URLs
        })

    def generate_sharing_data(self, wrapped_data, request):
        """Generate sharing text and URLs for social media platforms"""

        # Base sharing text
        share_text = (
            f"🎵 My Spotify Wrapped Stats:\n"
            f"• {wrapped_data['listeningTimeHours']} hours of music\n"
            f"• Top Artist: {wrapped_data['topArtists'][0]['name']}\n"
            f"• Top Track: {wrapped_data['topTracks'][0]['name']}\n"
            f"• {wrapped_data['totalArtists']} different artists\n"
            f"#SpotifyWrapped"
        )

        # Get the current page's URL
        current_url = request.build_absolute_uri()

        # Generate platform-specific sharing URLs
        sharing_data = {
            'twitter': {
                'url': f"https://twitter.com/intent/tweet?text={urllib.parse.quote(share_text)}&url={urllib.parse.quote(current_url)}"
            },
            'linkedin': {
                'url': f"https://www.linkedin.com/sharing/share-offsite/?url={urllib.parse.quote(current_url)}"
            },
            'instagram': {
                'text': share_text,  # For copying to clipboard since Instagram doesn't have a direct sharing API
                'url': current_url
            }
        }
        print(sharing_data)
        return sharing_data




print("dablt")

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