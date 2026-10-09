from flask import Flask, Response, jsonify, redirect, request, send_file, send_from_directory

import csv
import io
import threading
import time

import db
import spotify
import ytm

app = Flask(__name__, static_folder="static", static_url_path="/static")

job = {"running": False, "error": "", "started": 0, "finished": 0, "done_at_start": 0}


def count_done(counts):
    return counts.get("added", 0) + counts.get("not_found", 0)


def get_timer(counts):
    if not job["started"]:
        return 0, None
    end = job["finished"] or time.time()
    elapsed = int(end - job["started"])
    done_now = count_done(counts) - job["done_at_start"]
    left = counts.get("pending", 0) + counts.get("matched", 0)
    if job["running"] and done_now > 0:
        return elapsed, int(left * elapsed / done_now)
    return elapsed, None


def run_job():
    try:
        yt = ytm.get_client()
        playlist_id = ytm.get_playlist_id(yt)
        while True:
            tracks = db.get_tracks(ytm.BATCH_SIZE)
            if not tracks:
                break
            ytm.process_batch(yt, playlist_id, tracks)
    except Exception as e:
        job["error"] = str(e)
    job["finished"] = time.time()
    job["running"] = False


def start_job():
    if job["running"]:
        return
    job["running"] = True
    job["error"] = ""
    job["started"] = time.time()
    job["finished"] = 0
    job["done_at_start"] = count_done(db.count_by_status())
    threading.Thread(target=run_job, daemon=True).start()


@app.route("/")
def index():
    return send_from_directory("static", "index.html")


@app.route("/login")
def login():
    return redirect(spotify.get_login_url())


@app.route("/callback")
def callback():
    if "code" not in request.args:
        return "Spotify login failed: " + request.args.get("error", "no code in URL (" + request.url + ")"), 400
    spotify.finish_login(request.args["code"])
    return redirect("/")


@app.route("/fetch", methods=["POST"])
def fetch():
    tracks = spotify.fetch_liked_tracks()
    added = db.insert_new_tracks(tracks)
    return jsonify({"total": len(tracks), "new": added})


@app.route("/start", methods=["POST"])
def start():
    start_job()
    return jsonify({"ok": True})


@app.route("/sync", methods=["POST"])
def sync():
    tracks = spotify.fetch_liked_tracks()
    added = db.insert_new_tracks(tracks)
    start_job()
    return jsonify({"total": len(tracks), "new": added})


@app.route("/status")
def status():
    counts = db.count_by_status()
    elapsed, eta = get_timer(counts)
    return jsonify(
        {
            "logged_in": spotify.is_logged_in(),
            "counts": counts,
            "elapsed": elapsed,
            "eta": eta,
            "running": job["running"],
            "error": job["error"],
        }
    )


@app.route("/report")
def report():
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["title", "artist", "spotify url"])
    for track in db.get_not_found():
        writer.writerow([track["title"], track["artist"], "https://open.spotify.com/track/" + track["spotify_id"]])
    return Response(
        "﻿" + output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=not_found.csv"},
    )


@app.route("/sounds/error")
def error_sound():
    return send_file("C:/Windows/Media/Windows Critical Stop.wav")


if __name__ == "__main__":
    db.init_db()
    app.run(host="127.0.0.1", port=8888)
