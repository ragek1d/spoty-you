from flask import Flask, jsonify, redirect, request, send_from_directory

import db
import spotify

app = Flask(__name__, static_folder="static", static_url_path="/static")


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


@app.route("/status")
def status():
    return jsonify({"logged_in": spotify.is_logged_in(), "counts": db.count_by_status()})


if __name__ == "__main__":
    db.init_db()
    app.run(host="127.0.0.1", port=8888)
