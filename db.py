import sqlite3
from datetime import datetime, timedelta

DB_PATH = "citas.db"


def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        name TEXT,
        age INTEGER,
        gender TEXT,
        looking_for TEXT,
        country TEXT,
        bio TEXT,
        is_vip INTEGER DEFAULT 0,
        vip_until TEXT,
        likes_left INTEGER DEFAULT 20,
        referred_by INTEGER,
        banned INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS user_media (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        file_id TEXT,
        media_type TEXT,
        position INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS likes (
        from_id INTEGER,
        to_id INTEGER,
        is_super INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (from_id, to_id)
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS matches (
        user1 INTEGER,
        user2 INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (user1, user2)
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        from_id INTEGER,
        to_id INTEGER,
        text TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS reports (
        reporter_id INTEGER,
        reported_id INTEGER,
        reason TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS last_seen (
        user_id INTEGER PRIMARY KEY,
        last_date TEXT
    )""")
    conn.commit()
    conn.close()


def get_user(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    return row


def save_user(user_id, username, name, age, gender, looking_for, country, referred_by=None):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""INSERT OR REPLACE INTO users
        (user_id, username, name, age, gender, looking_for, country, referred_by)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (user_id, username, name, age, gender, looking_for, country, referred_by))
    conn.commit()
    conn.close()


def update_bio(user_id, bio):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE users SET bio = ? WHERE user_id = ?", (bio, user_id))
    conn.commit()
    conn.close()


def add_media(user_id, file_id, media_type, position):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""INSERT INTO user_media (user_id, file_id, media_type, position)
                 VALUES (?, ?, ?, ?)""", (user_id, file_id, media_type, position))
    conn.commit()
    conn.close()


def get_user_media(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT file_id, media_type FROM user_media WHERE user_id = ? ORDER BY position",
              (user_id,))
    rows = c.fetchall()
    conn.close()
    return rows


def count_user_media(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM user_media WHERE user_id = ?", (user_id,))
    n = c.fetchone()[0]
    conn.close()
    return n


def clear_media(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM user_media WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()


def get_random_profile(exclude_id, looking_for, country, is_vip):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    query = """SELECT user_id, name, age, gender, country, bio, is_vip
               FROM users
               WHERE user_id != ? AND name IS NOT NULL AND banned = 0
               AND gender = ?
               AND user_id NOT IN (SELECT to_id FROM likes WHERE from_id = ?)
               AND is_model = 0"""
    params = [exclude_id, looking_for, exclude_id]


    query += " ORDER BY RANDOM() LIMIT 1"
    c.execute(query, params)
    row = c.fetchone()
    conn.close()
    return row


def count_available_profiles(exclude_id, looking_for, country):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""SELECT COUNT(*) FROM users
                 WHERE user_id != ? AND gender = ? AND banned = 0
                 AND LOWER(country) = LOWER(?)""",
              (exclude_id, looking_for, country))
    n = c.fetchone()[0]
    conn.close()
    return n


def save_like(from_id, to_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO likes (from_id, to_id) VALUES (?, ?)",
              (from_id, to_id))
    conn.commit()
    conn.close()


def check_match(from_id, to_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT 1 FROM likes WHERE from_id = ? AND to_id = ?", (to_id, from_id))
    result = c.fetchone()
    conn.close()
    return result is not None


def create_match(user1, user2):
    a, b = sorted([user1, user2])
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO matches (user1, user2) VALUES (?, ?)", (a, b))
    conn.commit()
    conn.close()


def get_matches(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""SELECT u.user_id, u.name, u.age, u.country
                 FROM matches m
                 JOIN users u ON (u.user_id = CASE WHEN m.user1 = ? THEN m.user2 ELSE m.user1 END)
                 WHERE m.user1 = ? OR m.user2 = ?""",
              (user_id, user_id, user_id))
    rows = c.fetchall()
    conn.close()
    return rows


def save_message(from_id, to_id, text):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO messages (from_id, to_id, text) VALUES (?, ?, ?)",
              (from_id, to_id, text))
    conn.commit()
    conn.close()


def get_messages(user_id, other_id, limit=20):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""SELECT from_id, text, created_at FROM messages
                 WHERE (from_id = ? AND to_id = ?) OR (from_id = ? AND to_id = ?)
                 ORDER BY created_at DESC LIMIT ?""",
              (user_id, other_id, other_id, user_id, limit))
    rows = c.fetchall()
    conn.close()
    return rows


def set_vip(user_id, days=30):
    until = (datetime.now() + timedelta(days=days)).isoformat()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE users SET is_vip = 1, vip_until = ?, likes_left = 99999999 WHERE user_id = ?",
              (until, user_id))
    conn.commit()
    conn.close()


def check_vip_expired(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT is_vip, vip_until FROM users WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    if not row or not row[0]:
        return False
    if row[1] and datetime.fromisoformat(row[1]) < datetime.now():
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("UPDATE users SET is_vip = 0, likes_left = 20 WHERE user_id = ?", (user_id,))
        conn.commit()
        conn.close()
        return False
    return True


def use_like(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT likes_left FROM users WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    if not row or row[0] <= 0:
        conn.close()
        return False
    c.execute("UPDATE users SET likes_left = likes_left - 1 WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()
    return True


def report_user(reporter_id, reported_id, reason):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO reports (reporter_id, reported_id, reason) VALUES (?, ?, ?)",
              (reporter_id, reported_id, reason))
    conn.commit()
    conn.close()


def ban_user(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE users SET banned = 1 WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()


def count_users():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users")
    n = c.fetchone()[0]
    conn.close()
    return n


def count_vips():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users WHERE is_vip = 1")
    n = c.fetchone()[0]
    conn.close()
    return n


def get_referral_count(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users WHERE referred_by = ?", (user_id,))
    n = c.fetchone()[0]
    conn.close()
    return n



def apply_model(user_id, photo1, photo2):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""UPDATE users 
        SET model_status = 'pending', 
            model_photo1 = ?, 
            model_photo2 = ?,
            model_applied_at = CURRENT_TIMESTAMP
        WHERE user_id = ?""", (photo1, photo2, user_id))
    conn.commit()
    conn.close()


def approve_model(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE users SET is_model = 1, model_status = 'approved' WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()


def reject_model(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE users SET is_model = 0, model_status = 'rejected', model_photo1 = NULL, model_photo2 = NULL WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()


def get_pending_models():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT user_id, name, age, country, model_photo1, model_photo2 FROM users WHERE model_status = 'pending'")
    rows = c.fetchall()
    conn.close()
    return rows


def get_active_models():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT user_id, name, age, country, model_photo1 FROM users WHERE is_model = 1 ORDER BY RANDOM()")
    rows = c.fetchall()
    conn.close()
    return rows


def clear_old_likes(days=7):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM likes WHERE created_at < datetime('now', '-{} days')".format(days))
    conn.commit()
    conn.close()
