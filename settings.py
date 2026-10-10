import os

ENV_FILE = ".env"
KEYS = ["SPOTIPY_CLIENT_ID", "SPOTIPY_CLIENT_SECRET", "GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET"]


def load():
    os.environ.setdefault("SPOTIPY_REDIRECT_URI", "http://127.0.0.1:8888/callback")
    if not os.path.exists(ENV_FILE):
        return
    with open(ENV_FILE, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip())


def get():
    values = {}
    for key in KEYS:
        values[key] = os.environ.get(key, "")
    return values


def save(values):
    for key in KEYS:
        os.environ[key] = values.get(key, "").strip()
    with open(ENV_FILE, "w", encoding="utf-8") as f:
        for key in KEYS:
            f.write(key + "=" + os.environ[key] + "\n")
