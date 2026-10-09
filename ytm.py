import re
from difflib import SequenceMatcher

from ytmusicapi import YTMusic

MIN_SCORE = 70


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
