from flask import Flask, Response, jsonify, redirect, request, send_file, send_from_directory

import csv
import io
import threading
import time

import webview

import db
import spotify
import ytm

app = Flask(__name__, static_folder="static", static_url_path="/static")

MAX_FAILURES = 10
MAX_CHECKS = 3

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
    failures = 0
    checks = 0
    yt = None
    while True:
        try:
            if yt is None:
                yt = ytm.get_client()
                playlist_id = ytm.get_playlist_id(yt)
            tracks = db.get_tracks(ytm.BATCH_SIZE)
            if not tracks:
                missing = ytm.find_missing(yt, playlist_id)
                checks += 1
                if missing == 0:
                    break
                if checks >= MAX_CHECKS:
                    job["error"] = str(missing) + " tracks could not be added. Click Resume to try again."
                    break
                continue
            ytm.process_batch(yt, playlist_id, tracks)
            failures = 0
            job["error"] = ""
        except Exception as e:
            failures += 1
            if failures >= MAX_FAILURES or "401" in str(e):
                job["error"] = str(e)
                break
            wait = min(30 * failures, 300)
            job["error"] = str(e) + " (trying again in " + str(wait) + " seconds)"
            time.sleep(wait)
            yt = None
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


@app.route("/retry", methods=["POST"])
def retry_not_found():
    if not job["running"]:
        db.reset_not_found()
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


def run_server():
    app.run(host="127.0.0.1", port=8888)


if __name__ == "__main__":
    db.init_db()
    threading.Thread(target=run_server, daemon=True).start()
    screen = webview.screens[0]
    webview.settings["ALLOW_DOWNLOADS"] = True
    webview.create_window(
        "spoty-you",
        "http://127.0.0.1:8888",
        width=screen.width // 2,
        height=screen.height // 2,
        x=screen.width // 4,
        y=screen.height // 4,
        resizable=False,
    )
    webview.start()
