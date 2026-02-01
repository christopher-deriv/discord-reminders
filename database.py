import sqlite3
import os

DB_PATH = os.getenv("DB_PATH", "data/bot.db")

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_name TEXT NOT NULL,
                target_time TEXT NOT NULL,
                channel_id INTEGER NOT NULL,
                created_by INTEGER NOT NULL,
                UNIQUE(event_name, target_time)
            )
        """)
        conn.commit()

def add_reminder(event_name, target_time, channel_id, created_by):
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO reminders (event_name, target_time, channel_id, created_by)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(event_name, target_time) DO UPDATE SET
                    channel_id = excluded.channel_id,
                    created_by = excluded.created_by
            """, (event_name, target_time, channel_id, created_by))
            conn.commit()
            return True
    except Exception as e:
        print(f"Database error: {e}")
        return False

def get_reminders():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT event_name, target_time, channel_id FROM reminders")
        return cursor.fetchall()

def delete_reminder(reminder_id):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM reminders WHERE id = ?", (reminder_id,))
        conn.commit()

def get_all_reminders_full():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, event_name, target_time, channel_id FROM reminders")
        return cursor.fetchall()
