#ADITHYAVERSION
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from rest_framework.response import Response
from rest_framework.reverse import reverse_lazy
from rest_framework.views import APIView
from rest_framework import status
from requests import Request, post
from django.http import JsonResponse, Http404
from .models import Token
from .credentials import CLIENT_ID, CLIENT_SECRET, REDIRECT_URI, API_KEY
from .extras import create_or_update_tokens, is_spotify_authenticated, spotify_requests_execution
from collections import Counter
from datetime import datetime, timedelta
import sqlite3
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from rest_framework.permissions import IsAuthenticated
from django.core.serializers.json import DjangoJSONEncoder
import urllib.parse
#import google.generativeai as genai
import google.generativeai as genai
import os
from django.shortcuts import render  # Assuming the function is in utils.py

from django.shortcuts import render, redirect


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
    redirect_url = f"http://localhost:8000/spotify/wrapped/intro?code={code}"
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
import random
class GameView(APIView):
   def get(self, request, format=None):
       # Ensure we have a session
       if not request.session.session_key:
           request.session.create()


       time_range = request.GET.get('time_range', 'medium_term')


       # Validate time range
       valid_ranges = ['short_term', 'medium_term', 'long_term']
       if time_range not in valid_ranges:
           time_range = 'medium_term'


       # Fetch top tracks
       key = request.session.session_key
       top_tracks_endpoint = f"me/top/tracks?time_range={time_range}&limit=50"
       top_tracks_response = spotify_requests_execution(key, top_tracks_endpoint)


       # Prepare album data for the game
       album_game_data = []
       for track in top_tracks_response.get("items", []):
           album = track.get("album", {})


           # Ensure we have all required fields
           if (album.get("name") and
                   album.get("artists") and
                   album.get("images")):
               album_entry = {
                   "album_name": album["name"],
                   "artist": album["artists"][0]["name"],
                   "image": album["images"][0]["url"],
                   "album_id": album.get("id", str(hash(album["name"])))
               }
               album_game_data.append(album_entry)


       # Shuffle the albums to randomize game
       random.shuffle(album_game_data)


       # Select first 10 albums for the game or fewer if not enough
       selected_albums = album_game_data[:10]


       # Prepare albums with blanked-out names
       for album in selected_albums:
           # Create a blanked-out version of the album name
           words = album['album_name'].split()


           # Choose a random word to blank out
           blank_index = random.randint(0, len(words) - 1)
           original_word = words[blank_index]


           # Replace the chosen word with underscores
           words[blank_index] = '_' * len(original_word)


           # Store additional game information
           album['blanked_name'] = ' '.join(words)
           album['correct_word'] = original_word
           album['word_index'] = blank_index


       # Time range display names
       time_range_display = {
           'short_term': 'Last 4 Weeks',
           'medium_term': 'Last 6 Months',
           'long_term': 'All Time'
       }


       # Store game state in session
       request.session['spotify_game_albums'] = selected_albums
       request.session['spotify_game_session'] = {
           "current_round": 0,
           "total_rounds": len(selected_albums),
           "score": 0
       }
       request.session.modified = True


       # Structure the data for the frontend
       trapped_data = {
           "currentTimeRange": time_range,
           "timeRangeDisplay": time_range_display[time_range],
           "availableTimeRanges": [
               {'value': tr, 'display': time_range_display[tr]}
               for tr in valid_ranges
           ],
           "gameData": {
               "currentAlbum": selected_albums[0],
               "allAlbums": selected_albums,
               "gameSession": {
                   "current_round": 0,
                   "total_rounds": len(selected_albums),
                   "score": 0
               }
           }
       }


       # Return JSON for API consumption
       if request.headers.get('Accept') == 'application/json':
           return JsonResponse(trapped_data, encoder=DjangoJSONEncoder)


       # Otherwise render the template
       return render(request, "album_guessing_game.html", {
           "trapped_data": trapped_data,
           "page_title": f"Spotify Album Guessing Game",
       })


   def post(self, request, format=None):
       # Retrieve game state from session
       try:
           albums = request.session.get('spotify_game_albums', [])
           game_session = request.session.get('spotify_game_session', {})


           if not albums or not game_session:
               return JsonResponse({"error": "Game session not found"}, status=400)


           # Get submitted answer
           submitted_word = request.data.get('submittedWord', '').strip()


           # Check if answer is correct
           current_album = albums[game_session['current_round']]
           is_correct = (
                   submitted_word.lower() == current_album['correct_word'].lower()
           )


           # Update score
           if is_correct:
               game_session['score'] += 1


           # Move to next round
           game_session['current_round'] += 1


           # Check if game is over
           is_game_over = game_session['current_round'] >= game_session['total_rounds']


           # Prepare response
           response_data = {
               "isCorrect": is_correct,
               "correctWord": current_album['correct_word'],
               "score": game_session['score'],
               "currentRound": game_session['current_round'],
               "totalRounds": game_session['total_rounds'],
               "isGameOver": is_game_over
           }


           # If not game over, include next album
           if not is_game_over:
               response_data['nextAlbum'] = albums[game_session['current_round']]


           # Update session
           request.session['spotify_game_session'] = game_session
           request.session.modified = True


           return JsonResponse(response_data)


       except Exception as e:
           return JsonResponse({"error": str(e)}, status=500)
class SpotifyWrappedView(APIView):
   def get(self, request, format=None):
       key = self.request.session.session_key
       # Configure the API key for the genai module
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

       import google.generativeai as genai
       # 5. Get user profile
       profile_endpoint = "me"
       profile_response = spotify_requests_execution(key, profile_endpoint)
       # Extract top song names and their artists
       genai.configure(api_key=API_KEY)
       model = genai.GenerativeModel("gemini-1.5-flash")
       top_songs_and_artists = [
           f"{track['name']} by {', '.join(artist['name'] for artist in track['artists'])}"
           for track in top_tracks_response.get("items", [])[:5]
       ]
       top_songs_and_artists_str = "; ".join(top_songs_and_artists)




       # Generate dynamic description based on top songs and artists
       response = model.generate_content(
           f"Dynamically describe how someone who listens to my kind of music tends to act/think/dress. "
           f"These are my top songs and artists: {top_songs_and_artists_str}. Limit the response to less than 100 words."
       )
       print(response)
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
           "response": response,
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

    

from django.shortcuts import render
from django.shortcuts import render, redirect
from .models import SpotifyWrapped

from django.shortcuts import render
from .models import SpotifyWrapped

def savedwraps(request):
    # Fetch all saved SpotifyWrapped data for the logged-in user
    wraps = SpotifyWrapped.objects.filter(user=request.user).order_by('-created_at')

    # Structure the data to pass into the template
    context = {
        'wraps': wraps,
        'page_title': 'Your Saved Spotify Wrapped'
    }

    return render(request, "savedwraps.html", context)

def wrap_detail(request, id):
    # Get the SpotifyWrapped entry based on the provided id
    wrap = get_object_or_404(SpotifyWrapped, id=id)

    # Create context with the data for the selected wrap
    context = {
        'wrap': wrap,
        'page_title': f"Details for {wrap.time_range.capitalize()} Wrapped"
    }

    # Render the 'wrap_detail.html' template with the context
    return render(request, "wrap_detail.html", context)

class SpotifyWrappedOverviewView(APIView):
    def get(self, request, format=None):
        key = self.request.session.session_key
        time_range = request.GET.get('time_range', 'medium_term')
        valid_ranges = ['short_term', 'medium_term', 'long_term']
        time_range_display = {'short_term': 'Last 4 Weeks', 'medium_term': 'Last 6 Months', 'long_term': 'All Time'}

        if time_range not in valid_ranges:
            time_range = 'medium_term'

        # Fetch general stats from the session or cached endpoints
        top_artists_endpoint = f"me/top/artists?time_range={time_range}&limit=50"
        top_tracks_endpoint = f"me/top/tracks?time_range={time_range}&limit=50"
        top_artists_response = spotify_requests_execution(key, top_artists_endpoint)
        top_tracks_response = spotify_requests_execution(key, top_tracks_endpoint)

        all_artists = {artist["id"] for artist in top_artists_response.get("items", [])}
        all_tracks = {track["id"] for track in top_tracks_response.get("items", [])}
        all_albums = {track["album"]["id"] for track in top_tracks_response.get("items", [])}

        genres = []
        for artist in top_artists_response.get("items", []):
            genres.extend(artist.get("genres", []))
        top_genres = Counter(genres).most_common(5)

        wrapped_data = {
            "currentTimeRange": time_range,
            "timeRangeDisplay": time_range_display[time_range],
            "availableTimeRanges": [{'value': tr, 'display': time_range_display[tr]} for tr in valid_ranges],
            "totalArtists": len(all_artists),
            "totalTracks": len(all_tracks),
            "totalAlbums": len(all_albums),
            "topGenres": [{"name": genre, "count": count} for genre, count in top_genres],
        }

        wraps = SpotifyWrapped.objects.filter(user=request.user).order_by('-created_at')

        return render(request, "wrapped_overview.html", {"wrapped_data": wrapped_data, "wraps": wraps, "time_range" : time_range, "page_title": "Your Spotify Wrapped Overview"})


import logging
from django.shortcuts import render
from rest_framework.views import APIView

logger = logging.getLogger(__name__)
class SpotifyWrappedGenAIView(APIView):
    def get(self, request, format=None):
        # Get the session key for the request
        key = self.request.session.session_key

        # Get time range from query parameters, default to medium_term
        time_range = request.GET.get('time_range', 'medium_term')

        # Validate time range
        valid_ranges = ['short_term', 'medium_term', 'long_term']
        if time_range not in valid_ranges:
            logger.warning(f"Invalid time range: {time_range}. Defaulting to 'medium_term'.")
            time_range = 'medium_term'

        try:
            # Fetch top tracks data from Spotify API
            top_tracks_endpoint = f"me/top/tracks?time_range={time_range}&limit=50"
            top_tracks_response = spotify_requests_execution(key, top_tracks_endpoint)

            # Extract top song names and their artists
            top_songs_and_artists = [
                f"{track['name']} by {', '.join(artist['name'] for artist in track['artists'])}"
                for track in top_tracks_response.get("items", [])[:5]
            ]
            top_songs_and_artists_str = "; ".join(top_songs_and_artists)

            # Configure GenAI
            import google.generativeai as genai
            genai.configure(api_key=API_KEY)
            model = genai.GenerativeModel("gemini-1.5-flash")

            # Generate dynamic description based on top songs and artists
            response = model.generate_content(
                f"Dynamically describe how someone who listens to my kind of music tends to act/think/dress. "
                f"These are my top songs and artists: {top_songs_and_artists_str}. Limit the response to less than 100 words."
            )

            # Process the GenAI response
            wrapped_data = {
                "genaiResponse": response.text,
                "topSongsAndArtists": top_songs_and_artists
            }

            logger.info(f"Successfully generated GenAI response for top tracks")

        except Exception as e:
            logger.error(f"Error generating GenAI response: {str(e)}")
            wrapped_data = {
                "genaiResponse": "Unable to generate description.",
                "topSongsAndArtists": []
            }

        # Render the template with the data
        return render(request, "wrapped_genai.html", {
            "wrapped_data": wrapped_data,
            "page_title": "Your Music Personality",
            "time_range": time_range
        })


class SpotifyWrappedArtistsView(APIView):
    def get(self, request, format=None):
        # Get the session key for the request
        key = self.request.session.session_key

        # Get time range from query parameters, default to medium_term
        time_range = request.GET.get('time_range', 'medium_term')

        # Validate time range
        valid_ranges = ['short_term', 'medium_term', 'long_term']
        if time_range not in valid_ranges:
            logger.warning(f"Invalid time range: {time_range}. Defaulting to 'medium_term'.")
            time_range = 'medium_term'

        # Fetch top artists data from Spotify API
        top_artists_endpoint = f"me/top/artists?time_range={time_range}&limit=50"

        try:
            # Call the function that interacts with the Spotify API
            top_artists_response = spotify_requests_execution(key, top_artists_endpoint)
            logger.info(f"Fetched top artists for time range: {time_range}")

            # Process top artists data
            wrapped_data = {
                "topArtists": [
                    {
                        "name": artist["name"],
                        "subtitle": ", ".join(artist.get("genres", [])[:2]),  # Displaying up to 2 genres
                        "image": artist["images"][0]["url"] if artist.get("images") else None,
                        "popularity": artist.get("popularity", 0),
                        "spotifyUrl": artist["external_urls"]["spotify"]
                    }
                    for artist in top_artists_response.get("items", [])[:5]  # Limit to top 5 artists
                ]
            }

        except Exception as e:
            logger.error(f"Error fetching top artists: {str(e)}")
            wrapped_data = {"topArtists": []}

        # Render the template with the data
        return render(request, "wrapped_artists.html", {
            "wrapped_data": wrapped_data,
            "page_title": "Your Top Artists",
            "time_range": time_range  # Ensure time range is passed to the template
        })


class SpotifyWrappedTracksView(APIView):
    def get(self, request, format=None):
        key = self.request.session.session_key
        time_range = request.GET.get('time_range', 'medium_term')

        top_tracks_endpoint = f"me/top/tracks?time_range={time_range}&limit=50"
        top_tracks_response = spotify_requests_execution(key, top_tracks_endpoint)

        wrapped_data = {
            "topTracks": [
                {
                    "name": track["name"],
                    "subtitle": ", ".join(artist["name"] for artist in track["artists"]),
                    "image": track["album"]["images"][0]["url"] if track["album"].get("images") else None,
                    "albumName": track["album"]["name"],
                    "spotifyUrl": track["external_urls"]["spotify"],
                    "preview_url": track["preview_url"],  # Include preview URL
                }
                for track in top_tracks_response.get("items", [])[:5]
            ]
        }

        return render(request, "wrapped_tracks.html", {"wrapped_data": wrapped_data, 'time_range': time_range, "page_title": "Your Top Tracks"})

class SpotifyWrappedAlbumsView(APIView):
    def get(self, request, format=None):
        key = self.request.session.session_key
        time_range = request.GET.get('time_range', 'medium_term')

        top_tracks_endpoint = f"me/top/tracks?time_range={time_range}&limit=50"
        top_tracks_response = spotify_requests_execution(key, top_tracks_endpoint)

        wrapped_data = {
            "topAlbums": [
                {
                    "name": track["album"]["name"],
                    "subtitle": track["album"]["artists"][0]["name"],
                    "image": track["album"]["images"][0]["url"] if track["album"].get("images") else None,
                    "spotifyUrl": track["album"]["external_urls"]["spotify"]
                }
                for track in top_tracks_response.get("items", [])[:5]
            ]
        }

        return render(request, "wrapped_albums_locations.html", {"wrapped_data": wrapped_data, 'time_range': time_range, "page_title": "Your Top Albums"})



from collections import Counter
from django.shortcuts import render
from rest_framework.views import APIView # Assuming spotify_requests_execution is a utility function

class SpotifyWrappedProfileView(APIView):
    def get(self, request, *args, **kwargs):
        key = self.request.session.session_key
        time_range = request.GET.get('time_range', 'medium_term')

        # Configure the API key for the genai module
        # Get time range from query parameters, default to medium_ter

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
        # Extract top song names and their artists
        '''model = genai.GenerativeModel("gemini-1.5-flash")
        top_songs_and_artists = [
            f"{track['name']} by {', '.join(artist['name'] for artist in track['artists'])}"
            for track in top_tracks_response.get("items", [])[:5]
        ]
        top_songs_and_artists_str = "; ".join(top_songs_and_artists)

        # Generate dynamic description based on top songs and artists
        response = model.generate_content(
            f"Dynamically describe how someone who listens to my kind of music tends to act/think/dress. "
            f"These are my top songs and artists: {top_songs_and_artists_str}."
        )'''
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
        }

        # Time range display names

        time_range_display = {
            'short_term': 'Last 4 Weeks',
            'medium_term': 'Last 6 Months',
            'long_term': 'All Time'
        }
        return render(request, "wrapped_profile.html",{"wrapped_data": wrapped_data, 'time_range': time_range, "page_title": "Your Spotify Profile"})


from django.shortcuts import render
from django.http import JsonResponse
import requests

class TopLocationsView(APIView):
    def get(self, request, format=None):
        key = self.request.session.session_key
        time_range = request.GET.get('time_range', 'medium_term')

        valid_ranges = ['short_term', 'medium_term', 'long_term']
        if time_range not in valid_ranges:
            time_range = 'medium_term'

        # Fetch Top Tracks data directly
        top_tracks_endpoint = f"https://api.spotify.com/v1/me/top/tracks?time_range={time_range}&limit=50"
        headers = {'Authorization': f'Bearer {key}'}
        top_tracks_response = requests.get(top_tracks_endpoint, headers=headers).json()

        # Process top locations (markets)
        all_markets = set()
        for track in top_tracks_response.get("items", []):
            all_markets.update(track.get("available_markets", []))

        # Get the top locations (markets)
        top_locations = [
            {
                "name": market,
                "count": len([track for track in top_tracks_response.get("items", []) if market in track.get("available_markets", [])])
            }
            for market in list(all_markets)[:5]
        ]

        # Log data for debugging
        print("Wrapped Data:", {
            "timeRangeDisplay": {'short_term': 'Last 4 Weeks', 'medium_term': 'Last 6 Months', 'long_term': 'All Time'}[time_range],
            "topLocations": top_locations
        })

        # Structure the data for the frontend
        wrapped_data = {
            "timeRangeDisplay": {'short_term': 'Last 4 Weeks', 'medium_term': 'Last 6 Months', 'long_term': 'All Time'}[time_range],
            "topLocations": top_locations
        }

        # Return JSON or render template
        if request.headers.get('Accept') == 'application/json':
            return JsonResponse(wrapped_data)

        return render(request, "top_locations.html", {"wrapped_data": wrapped_data})


class TopGenresView(APIView):
    def get(self, request, format=None):
        key = self.request.session.session_key
        time_range = request.GET.get('time_range', 'medium_term')

        valid_ranges = ['short_term', 'medium_term', 'long_term']
        if time_range not in valid_ranges:
            time_range = 'medium_term'

        # Fetch Top Artists data
        top_artists_endpoint = f"me/top/artists?time_range={time_range}&limit=50"
        top_artists_response = spotify_requests_execution(key, top_artists_endpoint)

        # Process top genres
        genres = []
        for artist in top_artists_response.get("items", []):
            genres.extend(artist.get("genres", []))
        top_genres = Counter(genres).most_common(5)

        # Structure the data for the frontend
        wrapped_data = {
            "timeRangeDisplay": {'short_term': 'Last 4 Weeks', 'medium_term': 'Last 6 Months', 'long_term': 'All Time'}[
                time_range],
            "topGenres": [{"name": genre, "count": count} for genre, count in top_genres]
        }

        # Return JSON or render template
        if request.headers.get('Accept') == 'application/json':
            return JsonResponse(wrapped_data)

        return render(request, "top_genres.html", {"wrapped_data": wrapped_data})


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


def saved_spotify_wrapped_artists(request, id):
    user = request.user

    # Get the specific wrap by id
    wrap = get_object_or_404(SpotifyWrapped, id=id, user=user)

    # Render the wrapped_profile.html template with the wrap context
    return render(request, "saved_artists.html", {
        "wrap": wrap,
        "page_title": "Your Saved Spotify Profile",
    })



def saved_spotify_wrapped_tracks(request, id):
    user = request.user

    # Get the specific wrap by id
    wrap = get_object_or_404(SpotifyWrapped, id=id, user=user)

    # Render the wrapped_profile.html template with the wrap context
    return render(request, "saved_tracks.html", {
        "wrap": wrap,
        "page_title": "Your Saved Spotify Profile",
    })


def saved_spotify_wrapped_albums(request, id):
    user = request.user

    # Get the specific wrap by id
    wrap = get_object_or_404(SpotifyWrapped, id=id, user=user)

    # Render the wrapped_profile.html template with the wrap context
    return render(request, "saved_albums.html", {
        "wrap": wrap,
        "page_title": "Your Saved Spotify Profile",
    })


def saved_spotify_wrapped_profile(request, id):
    user = request.user

    # Get the specific wrap by id
    wrap = get_object_or_404(SpotifyWrapped, id=id, user=user)

    # Render the wrapped_profile.html template with the wrap context
    return render(request, "saved_profile.html", {
        "wrap": wrap,
        "page_title": "Your Saved Spotify Profile",
    })


def delete_spotify_wrap(request, id):
    try:
        wrap = SpotifyWrapped.objects.get(id=id, user=request.user)
    except SpotifyWrapped.DoesNotExist:
        raise Http404("Spotify Wrapped data not found.")

        # Delete the wrap
    wrap.delete()

    # Redirect back to the list of wraps
    return redirect('wrapped_intro')