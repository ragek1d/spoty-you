import sqlite3

DB_FILE = "spoty.db"


def connect():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = connect()
    conn.execute(
        """CREATE TABLE IF NOT EXISTS tracks (
            spotify_id TEXT PRIMARY KEY,
            title TEXT,
            artist TEXT,
            duration INTEGER,
            video_id TEXT,
            status TEXT DEFAULT 'pending'
        )"""
    )
    conn.commit()
    conn.close()


def insert_new_tracks(tracks):
    conn = connect()
    added = 0
    for t in tracks:
        cur = conn.execute(
            "INSERT OR IGNORE INTO tracks (spotify_id, title, artist, duration) VALUES (?, ?, ?, ?)",
            (t["spotify_id"], t["title"], t["artist"], t["duration"]),
        )
        added += cur.rowcount
    conn.commit()
    conn.close()
    return added


def get_tracks(limit):
    conn = connect()
    rows = conn.execute("SELECT * FROM tracks WHERE status = 'pending' LIMIT ?", (limit,)).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def count_by_status():
    conn = connect()
    rows = conn.execute("SELECT status, COUNT(*) AS n FROM tracks GROUP BY status").fetchall()
    conn.close()
    return {row["status"]: row["n"] for row in rows}
