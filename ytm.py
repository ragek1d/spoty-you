import os
import re
import time
from difflib import SequenceMatcher

from ytmusicapi import YTMusic

import db

MIN_SCORE = 70
PLAYLIST_NAME = "Spotify Liked Songs"
PLAYLIST_FILE = "playlist_id.txt"
BATCH_SIZE = 50


def get_client():
    return YTMusic("headers_auth.json")


def normalize(text):
    text = text.lower()
    text = re.sub(r"\(.*?\)|\[.*?\]", " ", text)
    text = re.sub(r"[^\w\s]", " ", text)
    return " ".join(text.split())


def score(track, result):
    title_score = SequenceMatcher(None, normalize(track["title"]), normalize(result["title"])).ratio() * 50

    wanted_artist = normalize(track["artist"])
    result_artists = [normalize(a["name"]) for a in result.get("artists") or []]
    artist_score = 30 if wanted_artist in result_artists else 0

    duration_score = 0
    if result.get("duration_seconds") and abs(result["duration_seconds"] - track["duration"]) <= 3:
        duration_score = 20

    return title_score + artist_score + duration_score


def find_video_id(yt, track):
    results = yt.search(track["artist"] + " " + track["title"], filter="songs", limit=5)
    best_id = None
    best_score = 0
    for result in results:
        s = score(track, result)
        if s > best_score:
            best_id = result["videoId"]
            best_score = s
    if best_score >= MIN_SCORE:
        return best_id, best_score
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
    results = []
    to_add = []
    for track in tracks:
        video_id = track["video_id"]
        if not video_id:
            video_id, _ = retry(find_video_id, yt, track)
            time.sleep(0.3)
        if video_id:
            results.append((video_id, "matched", track["spotify_id"]))
            to_add.append(video_id)
        else:
            results.append((None, "not_found", track["spotify_id"]))

    if to_add:
        retry(yt.add_playlist_items, playlist_id, to_add, duplicates=False)
        results = [(v, "added" if s == "matched" else s, i) for v, s, i in results]

    db.save_results(results)
    time.sleep(1)
    return len(to_add), len(tracks) - len(to_add)
