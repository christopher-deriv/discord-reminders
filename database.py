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
                guild_id INTEGER NOT NULL,
                event_name TEXT NOT NULL,
                target_time TEXT NOT NULL,
                channel_id INTEGER NOT NULL,
                created_by INTEGER NOT NULL,
                gif_url TEXT,
                recurrence TEXT DEFAULT 'daily',
                target_date TEXT,
                UNIQUE(guild_id, event_name, target_time, recurrence)
            )
        """)
        conn.commit()

def add_reminder(guild_id, event_name, target_time, channel_id, created_by, gif_url=None, recurrence='daily', target_date=None):
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO reminders (guild_id, event_name, target_time, channel_id, created_by, gif_url, recurrence, target_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(guild_id, event_name, target_time, recurrence) DO UPDATE SET
                    channel_id = excluded.channel_id,
                    created_by = excluded.created_by,
                    gif_url = excluded.gif_url,
                    target_date = excluded.target_date
            """, (guild_id, event_name, target_time, channel_id, created_by, gif_url, recurrence, target_date))
            conn.commit()
            return True
    except Exception as e:
        print(f"Database error: {e}")
        return False

def get_reminders():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, event_name, target_time, channel_id, gif_url, recurrence, target_date FROM reminders")
        return cursor.fetchall()

def delete_reminder(reminder_id):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM reminders WHERE id = ?", (reminder_id,))
        conn.commit()

def get_all_reminders_full(guild_id):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, event_name, target_time, channel_id, gif_url, recurrence, target_date FROM reminders WHERE guild_id = ?", (guild_id,))
        return cursor.fetchall()

def update_reminder(reminder_id, event_name, target_time, gif_url=None):
    # Note: For simplicity, we aren't updating recurrence/date via the quick edit modal yet, 
    # but the function signature remains compatible for now.
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            query = "UPDATE reminders SET event_name = ?, target_time = ?"
            params = [event_name, target_time]
            if gif_url:
                query += ", gif_url = ?"
                params.append(gif_url)
            query += " WHERE id = ?"
            params.append(reminder_id)
            
            cursor.execute(query, tuple(params))
            conn.commit()
            return True
    except Exception as e:
        print(f"Database error: {e}")
        return False
