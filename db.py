import sqlite3

DB_FILE = "spoty.db"
KEYS = {"tracks": "spotify_id", "yt_tracks": "video_id"}


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
    conn.execute(
        """CREATE TABLE IF NOT EXISTS yt_tracks (
            video_id TEXT PRIMARY KEY,
            title TEXT,
            artist TEXT,
            duration INTEGER,
            spotify_id TEXT,
            status TEXT DEFAULT 'pending'
        )"""
    )
    for table in KEYS:
        columns = [row["name"] for row in conn.execute("PRAGMA table_info(" + table + ")")]
        if "copied" not in columns:
            conn.execute("ALTER TABLE " + table + " ADD COLUMN copied INTEGER DEFAULT 0")
    conn.commit()
    conn.close()


def insert_new_tracks(tracks, table="tracks"):
    key = KEYS[table]
    conn = connect()
    added = 0
    for t in tracks:
        cur = conn.execute(
            "INSERT OR IGNORE INTO " + table + " (" + key + ", title, artist, duration) VALUES (?, ?, ?, ?)",
            (t[key], t["title"], t["artist"], t["duration"]),
        )
        added += cur.rowcount
    conn.commit()
    conn.close()
    return added


def get_tracks(limit, table="tracks"):
    conn = connect()
    rows = conn.execute(
        "SELECT * FROM " + table + " WHERE status IN ('pending', 'matched') ORDER BY rowid LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def save_results(results):
    conn = connect()
    conn.executemany("UPDATE tracks SET video_id = ?, status = ? WHERE spotify_id = ?", results)
    conn.commit()
    conn.close()


def save_spotify_results(results):
    conn = connect()
    conn.executemany("UPDATE yt_tracks SET spotify_id = ?, status = ? WHERE video_id = ?", results)
    conn.commit()
    conn.close()


def set_copied(table, track_id, copied):
    conn = connect()
    conn.execute("UPDATE " + table + " SET copied = ? WHERE " + KEYS[table] + " = ?", (copied, track_id))
    conn.commit()
    conn.close()


def get_added_video_ids():
    conn = connect()
    rows = conn.execute("SELECT video_id FROM tracks WHERE status = 'added'").fetchall()
    conn.close()
    return {row["video_id"] for row in rows}


def reset_missing(video_ids_in_playlist):
    conn = connect()
    rows = conn.execute("SELECT spotify_id, video_id FROM tracks WHERE status = 'added'").fetchall()
    missing = 0
    for row in rows:
        if row["video_id"] not in video_ids_in_playlist:
            conn.execute("UPDATE tracks SET status = 'matched' WHERE spotify_id = ?", (row["spotify_id"],))
            missing += 1
    conn.commit()
    conn.close()
    return missing


def reset_not_found(table="tracks"):
    conn = connect()
    conn.execute("UPDATE " + table + " SET status = 'pending' WHERE status = 'not_found'")
    conn.commit()
    conn.close()


def get_not_found(table="tracks"):
    conn = connect()
    rows = conn.execute("SELECT * FROM " + table + " WHERE status = 'not_found'").fetchall()
    conn.close()
    return [dict(row) for row in rows]


def count_by_status(table="tracks"):
    conn = connect()
    rows = conn.execute("SELECT status, COUNT(*) AS n FROM " + table + " GROUP BY status").fetchall()
    conn.close()
    return {row["status"]: row["n"] for row in rows}
