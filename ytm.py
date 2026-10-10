import json
import os
import re
import time
from difflib import SequenceMatcher

from ytmusicapi import OAuthCredentials, YTMusic

import db

MIN_SCORE = 70
PLAYLIST_NAME = "Spotify Liked Songs"
PLAYLIST_FILE = "playlist_id.txt"
AUTH_FILE = "headers_auth.json"
OAUTH_FILE = "oauth.json"
BATCH_SIZE = 50
MAX_DURATION_DIFFERENCE = 20

CYRILLIC = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e", "ж": "zh", "з": "z",
    "и": "i", "й": "y", "к": "k", "л": "l", "м": "m", "н": "n", "о": "o", "п": "p", "р": "r",
    "с": "s", "т": "t", "у": "u", "ф": "f", "х": "kh", "ц": "ts", "ч": "ch", "ш": "sh",
    "щ": "shch", "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya",
}


def get_credentials():
    return OAuthCredentials(os.environ.get("GOOGLE_CLIENT_ID", ""), os.environ.get("GOOGLE_CLIENT_SECRET", ""))


def get_client():
    if os.path.exists(OAUTH_FILE):
        return YTMusic(OAUTH_FILE, oauth_credentials=get_credentials())
    return YTMusic(AUTH_FILE)


def is_logged_in():
    return os.path.exists(AUTH_FILE) or os.path.exists(OAUTH_FILE)


def get_login_code():
    return get_credentials().get_code()


def finish_code_login(device_code):
    token = get_credentials().token_from_code(device_code)
    if "access_token" not in token:
        return False
    token["expires_at"] = int(time.time()) + token["expires_in"]
    with open(OAUTH_FILE, "w", encoding="utf-8") as f:
        json.dump(token, f)
    if os.path.exists(AUTH_FILE):
        os.remove(AUTH_FILE)
    return True


def save_cookies(cookie_text):
    if os.path.exists(OAUTH_FILE):
        os.remove(OAUTH_FILE)
    headers = {
        "accept": "*/*",
        "authorization": "SAPISIDHASH",
        "content-type": "application/json",
        "x-goog-authuser": "0",
        "x-origin": "https://music.youtube.com",
        "cookie": cookie_text,
    }
    with open(AUTH_FILE, "w", encoding="utf-8") as f:
        json.dump(headers, f)


def normalize(text):
    text = text.lower()
    text = re.sub(r"\(.*?\)|\[.*?\]", " ", text)
    text = re.sub(r"[^\w\s]", " ", text)
    return " ".join(text.split())


def plain(text):
    return " ".join(re.sub(r"[^\w\s]", " ", text.lower()).split())


def short_title(title):
    return title.split(" - ")[0]


def similarity(a, b):
    return SequenceMatcher(None, a, b).ratio()


def title_similarity(a, b):
    return max(
        similarity(normalize(a), normalize(b)),
        similarity(normalize(short_title(a)), normalize(short_title(b))),
        similarity(plain(a), plain(b)),
    )


def to_latin(text):
    return "".join(CYRILLIC.get(letter, letter) for letter in text)


def same_artist(wanted, name):
    if not wanted or not name:
        return False
    if wanted in name or name in wanted:
        return True
    return similarity(to_latin(wanted), to_latin(name)) >= 0.8


def score(track, result):
    wanted_artist = normalize(track["artist"])
    artist_found = False
    for artist in result.get("artists") or []:
        if same_artist(wanted_artist, normalize(artist["name"])):
            artist_found = True
    if not artist_found:
        return 0

    title_score = title_similarity(track["title"], result["title"]) * 50

    difference = 999
    if result.get("duration_seconds"):
        difference = abs(result["duration_seconds"] - track["duration"])
    duration_score = 20 if difference <= 3 else 0
    if difference != 999 and difference > MAX_DURATION_DIFFERENCE:
        return 0

    # same song with the title in another language (for example Korean and English)
    if difference <= 1 and track["title"].isascii() != result["title"].isascii():
        return MIN_SCORE

    return title_score + 30 + duration_score


def find_video_id(yt, track):
    queries = [track["artist"] + " " + track["title"]]
    if short_title(track["title"]) != track["title"]:
        queries.append(track["artist"] + " " + short_title(track["title"]))

    best_id = None
    best_score = 0
    for query in queries:
        for result in yt.search(query, filter="songs", limit=5):
            s = score(track, result)
            if result.get("videoId") and s > best_score:
                best_id = result["videoId"]
                best_score = s
        if best_score >= MIN_SCORE:
            return best_id, best_score
        time.sleep(0.3)
    return None, best_score


def retry(func, *args, **kwargs):
    for attempt in range(3):
        try:
            return func(*args, **kwargs)
        except Exception:
            if attempt == 2:
                raise
            time.sleep(5)


def get_playlist_id(yt):
    if os.path.exists(PLAYLIST_FILE):
        with open(PLAYLIST_FILE, encoding="utf-8") as f:
            return f.read().strip()
    playlist_id = yt.create_playlist(PLAYLIST_NAME, "Copied from Spotify Liked Songs", "PRIVATE")
    with open(PLAYLIST_FILE, "w", encoding="utf-8") as f:
        f.write(playlist_id)
    return playlist_id


def process_batch(yt, playlist_id, tracks):
    already_added = db.get_added_video_ids()
    results = []
    to_add = []
    last_error = None
    for track in tracks:
        video_id = track["video_id"]
        if not video_id:
            try:
                video_id, _ = retry(find_video_id, yt, track)
            except Exception as e:
                last_error = e
                continue
            time.sleep(0.3)
        if not video_id:
            results.append((None, "not_found", track["spotify_id"]))
        elif video_id in already_added:
            results.append((video_id, "added", track["spotify_id"]))
        else:
            already_added.add(video_id)
            to_add.append(video_id)
            results.append((video_id, "matched", track["spotify_id"]))

    if not results and last_error:
        raise last_error

    db.save_results(results)

    if to_add:
        response = retry(yt.add_playlist_items, playlist_id, to_add, duplicates=True)
        status = response.get("status") if isinstance(response, dict) else response
        if "SUCCEEDED" not in str(status):
            raise Exception("YouTube Music did not add the tracks: " + str(status)[:200])
        db.save_results([(v, "added" if s == "matched" else s, i) for v, s, i in results])

    time.sleep(1)


def find_missing(yt, playlist_id):
    playlist = retry(yt.get_playlist, playlist_id, limit=None)
    tracks = playlist["tracks"]
    if playlist.get("trackCount") and len(tracks) < playlist["trackCount"]:
        raise Exception("Could not load the whole playlist to check it")
    return db.reset_missing({t["videoId"] for t in tracks})
