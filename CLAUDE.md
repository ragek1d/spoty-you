# spoty-you

Local tool: copy Spotify "Liked Songs" (~3000 tracks) into a YouTube Music playlist.
Repo: https://github.com/ragek1d/spoty-you
Owner is a beginner in Python: keep code simple, readable, no clever tricks.

## Stack
- Python 3.11+, Flask (single process, localhost only), vanilla HTML/CSS/JS (no frameworks, no build step)
- spotipy (Spotify OAuth, scope: user-library-read)
- ytmusicapi (YouTube Music search + playlist add, no strict quota)
- sqlite3 (stdlib) for state. No other dependencies without asking.

## Structure
- app.py        Flask routes + progress endpoint (SSE or polling), opens the pywebview window (fixed, 1/4 of the screen)
- settings.py   read/write keys in .env (edited from the Settings screen)
- build.bat     PyInstaller build -> dist\spoty-you\spoty-you.exe (data files live next to the exe)
- spotify.py    login, fetch liked tracks
- ytm.py        search, match, add to playlist; login via window cookies (headers_auth.json) or device code (oauth.json)
- reverse.py    YouTube Music playlist -> Spotify Liked Songs (search on Spotify, save with PUT /me/library, 40 per request)
- db.py         SQLite: tracks(spotify_id, title, artist, duration, video_id, status, copied), yt_tracks (same, keyed by video_id) for the reverse direction
- static/       index.html, style.css, app.js
- secrets live in .env and headers_auth.json (both in .gitignore, never commit)

## Behavior
- Flow: Spotify login -> fetch liked -> match each track -> add in batches -> report
- Status per track: pending / matched / added / not_found. Resume = process only non-added rows.
- Sync = fetch liked again, insert new spotify_ids only, process those.
- Matching: ytmusicapi search with filter="songs", score by normalized title + artist + duration (+-3s). Plain code, no LLM calls.
- Add videoIds in batches (~50), small sleep between requests, retry on error, save status after every batch.
- Report: not_found.csv (title, artist, spotify url).

## UI
- English only. Windows 7 Frutiger Aero: glossy aqua/green gradients, glass panels with blur and soft shadows, rounded corners, bubbles/sky background, Segoe UI.
- Frameless window: own minimize/close buttons, drag by the background.
- Progress bar, buttons: Spotify login, YouTube login, Start, Resume, Stop, Sync, Retry not found, Not found list, Settings, swap direction.
- Port 8888 is fixed: never test while the user's own copy of the app is running (use another port and data folder).

## Commands
- Setup: pip install -r requirements.txt
- Run: python app.py (opens the app window; server on http://127.0.0.1:8888)
- Build: build.bat
- Spotify redirect URI: http://127.0.0.1:8888/callback

## Token-saving rules
- Answers short: no recaps, no repeating code I can see in the diff.
- Targeted edits only (Edit tool); never rewrite whole files.
- Read only files needed for the task; do not scan the repo.
- Use graphify for the code map; query it instead of reading many files. Rebuild after structural changes. Do not paste its output into chat.
- One feature at a time: minimal working version first, then extend.
- No extra comments, docstrings, tests, or abstractions unless asked.
- Commit small and often, short messages, push to the repo above.
