import requests
from .credentials import CLIENT_ID, CLIENT_SECRET, REDIRECT_URI
from .models import Token
from django.utils import timezone
from datetime import timedelta
from requests import post

BASE_URL = 'https://api.spotify.com/v1/me'

def check_tokens(session_id):
    tokens = Token.objects.filter(user=session_id).first()
    return tokens  # returns None if no tokens found

def create_or_update_tokens(session_id, access_token, refresh_token, expires_in, token_type):
    if expires_in is None:
        expires_in = 3600  # Default to 1 hour if not provided
    expires_in_time = timezone.now() + timedelta(seconds=expires_in)

    tokens = check_tokens(session_id)
    if tokens:
        tokens.access_token = access_token
        tokens.refresh_token = refresh_token
        tokens.expires_in = expires_in_time
        tokens.token_type = token_type
        tokens.save(update_fields=['access_token', 'refresh_token', 'expires_in', 'token_type'])
    else:
        Token.objects.create(
            user=session_id,
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=expires_in_time,
            token_type=token_type,
        )

def is_spotify_authenticated(session_id):
    tokens = check_tokens(session_id)
    if tokens:
        if tokens.expires_in <= timezone.now():
            # Refresh the token if expired
            refresh_token_func(session_id)
            tokens = check_tokens(session_id)  # Reload tokens after refresh
        return True if tokens.access_token else False
    return False

def refresh_token_func(session_id):
    tokens = check_tokens(session_id)
    if not tokens:
        return False  # No token to refresh

    response = post('https://accounts.spotify.com/api/token', data={
        'grant_type': 'refresh_token',
        'refresh_token': tokens.refresh_token,
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
    })

    if response.status_code == 200:
        response_data = response.json()
        access_token = response_data.get('access_token')
        expires_in = response_data.get('expires_in', 3600)  # Fallback to 1 hour
        token_type = response_data.get('token_type')

        # Update tokens
        create_or_update_tokens(
            session_id=session_id,
            access_token=access_token,
            refresh_token=tokens.refresh_token,
            expires_in=expires_in,
            token_type=token_type,
        )
    else:
        print("Error refreshing token:", response.status_code, response.text)
        return False
    return True

def spotify_requests_execution(session_id, endpoint):
    if not is_spotify_authenticated(session_id):
        return {"error": "Authentication required"}

    tokens = check_tokens(session_id)
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {tokens.access_token}'
    }

    response = requests.get(f"{BASE_URL}/{endpoint}", headers=headers)

    if response.status_code == 200:
        return response.json()
    else:
        print("Error with request:", response.status_code, response.text)
        return {'Error': 'Issue with Spotify API request'}
