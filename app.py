from flask import Flask, Response, jsonify, redirect, request, send_from_directory

import csv
import io
import threading

import db
import spotify
import ytm

app = Flask(__name__, static_folder="static", static_url_path="/static")

job = {"running": False, "error": ""}


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
    job["running"] = False


def start_job():
    if job["running"]:
        return
    job["running"] = True
    job["error"] = ""
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
    return jsonify(
        {
            "logged_in": spotify.is_logged_in(),
            "counts": db.count_by_status(),
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


if __name__ == "__main__":
    db.init_db()
    app.run(host="127.0.0.1", port=8888)
