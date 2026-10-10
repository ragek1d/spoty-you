import os
import spotipy
from spotipy.oauth2 import SpotifyOAuth

import settings


settings.load()


def has_keys():
    return bool(os.environ.get("SPOTIPY_CLIENT_ID") and os.environ.get("SPOTIPY_CLIENT_SECRET"))


def get_auth():
    return SpotifyOAuth(scope="user-library-read user-library-modify", cache_path=".cache")


def get_client():
    return spotipy.Spotify(auth_manager=get_auth())


def get_login_url():
    return get_auth().get_authorize_url()


def finish_login(code):
    get_auth().get_access_token(code, as_dict=False)


def is_logged_in():
    return has_keys() and get_auth().get_cached_token() is not None


def fetch_liked_tracks():
    sp = spotipy.Spotify(auth_manager=get_auth())
    tracks = []
    offset = 0
    while True:
        page = sp.current_user_saved_tracks(limit=50, offset=offset)
        for item in page["items"]:
            track = item["track"]
            if track is None:
                continue
            tracks.append(
                {
                    "spotify_id": track["id"],
                    "title": track["name"],
                    "artist": track["artists"][0]["name"],
                    "duration": track["duration_ms"] // 1000,
                }
            )
        if page["next"] is None:
            break
        offset += 50
    return tracks
