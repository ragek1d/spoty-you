import time

import db
import ytm

BATCH_SIZE = 40


def get_playlists(yt):
    playlists = []
    for playlist in yt.get_library_playlists(limit=None):
        playlists.append({"id": playlist["playlistId"], "title": playlist["title"]})
    return playlists


def fetch_playlist_tracks(yt, playlist_id):
    playlist = yt.get_playlist(playlist_id, limit=None)
    tracks = []
    for item in playlist["tracks"]:
        if not item.get("videoId"):
            continue
        artists = item.get("artists") or []
        tracks.append(
            {
                "video_id": item["videoId"],
                "title": item["title"],
                "artist": artists[0]["name"] if artists else "",
                "duration": item.get("duration_seconds") or 0,
            }
        )
    # oldest first, so the newest track ends up on top in Spotify
    tracks.reverse()
    return tracks


def search_spotify(sp, track):
    best_id = None
    best_score = 0
    query = track["artist"] + " " + ytm.short_title(track["title"])
    for item in sp.search(q=query, type="track", limit=5)["tracks"]["items"]:
        result = {
            "title": item["name"],
            "artists": item["artists"],
            "duration_seconds": item["duration_ms"] // 1000,
        }
        s = ytm.score(track, result)
        # music videos are longer or shorter than the song itself, so trust a very close title
        if s == 0 and ytm.title_similarity(track["title"], item["name"]) >= 0.9:
            same_length = dict(track)
            same_length["duration"] = result["duration_seconds"]
            s = ytm.score(same_length, result)
        if s > best_score:
            best_id = item["id"]
            best_score = s
    if best_score >= ytm.MIN_SCORE:
        return best_id
    return None


def find_spotify_id(sp, track):
    spotify_id = search_spotify(sp, track)
    # music videos are often named "Artist - Title" and uploaded by another channel
    if not spotify_id and " - " in track["title"]:
        artist, title = track["title"].split(" - ", 1)
        time.sleep(0.3)
        spotify_id = search_spotify(sp, {"artist": artist, "title": title, "duration": track["duration"]})
    return spotify_id


def process_batch(sp, tracks, job):
    results = []
    to_add = []
    for track in tracks:
        if job["stop"]:
            break
        spotify_id = track["spotify_id"]
        if not spotify_id:
            spotify_id = ytm.retry(find_spotify_id, sp, track)
            time.sleep(0.3)
        if not spotify_id:
            results.append((None, "not_found", track["video_id"]))
        else:
            to_add.append(spotify_id)
            results.append((spotify_id, "matched", track["video_id"]))

    db.save_spotify_results(results)

    if to_add:
        uris = ",".join("spotify:track:" + spotify_id for spotify_id in to_add)
        ytm.retry(sp._put, "me/library?uris=" + uris)
        db.save_spotify_results([(i, "added" if s == "matched" else s, v) for i, s, v in results])
