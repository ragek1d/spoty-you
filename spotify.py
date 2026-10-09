import os
import spotipy
from spotipy.oauth2 import SpotifyOAuth


def load_env():
    if not os.path.exists(".env"):
        return
    with open(".env", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip())


load_env()

auth = SpotifyOAuth(scope="user-library-read", cache_path=".cache")


def get_login_url():
    return auth.get_authorize_url()


def finish_login(code):
    auth.get_access_token(code, as_dict=False)


def is_logged_in():
    return auth.get_cached_token() is not None


def fetch_liked_tracks():
    sp = spotipy.Spotify(auth_manager=auth)
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
