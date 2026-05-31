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
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS alliance_players (
                discord_id INTEGER NOT NULL,
                guild_id INTEGER NOT NULL,
                player_id TEXT NOT NULL,
                player_name TEXT,
                PRIMARY KEY (guild_id, player_id)
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS redemption_history (
                player_id TEXT NOT NULL,
                gift_code TEXT NOT NULL,
                redeemed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (player_id, gift_code)
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS active_gift_codes (
                gift_code TEXT PRIMARY KEY,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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

def update_reminder_date(reminder_id, new_target_date):
    """Updates only the target_date for a specific reminder."""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE reminders SET target_date = ? WHERE id = ?", (new_target_date, reminder_id))
            conn.commit()
            return True
    except Exception as e:
        print(f"Database error (update_reminder_date): {e}")
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

def register_player(discord_id, guild_id, player_id, player_name):
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO alliance_players (discord_id, guild_id, player_id, player_name)
                VALUES (?, ?, ?, ?)
            """, (discord_id, guild_id, player_id, player_name))
            conn.commit()
            return True
    except Exception as e:
        print(f"Database error (register_player): {e}")
        return False

def unregister_player(discord_id, guild_id, player_id):
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM alliance_players
                WHERE discord_id = ? AND guild_id = ? AND player_id = ?
            """, (discord_id, guild_id, player_id))
            conn.commit()
            return True
    except Exception as e:
        print(f"Database error (unregister_player): {e}")
        return False

def get_registered_players(discord_id, guild_id):
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT player_id, player_name FROM alliance_players
                WHERE discord_id = ? AND guild_id = ?
            """, (discord_id, guild_id))
            return cursor.fetchall()
    except Exception as e:
        print(f"Database error (get_registered_players): {e}")
        return []

def get_all_guild_players(guild_id):
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT discord_id, player_id, player_name FROM alliance_players
                WHERE guild_id = ?
            """, (guild_id,))
            return cursor.fetchall()
    except Exception as e:
        print(f"Database error (get_all_guild_players): {e}")
        return []

def add_redemption_record(player_id, gift_code):
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR IGNORE INTO redemption_history (player_id, gift_code)
                VALUES (?, ?)
            """, (player_id, gift_code))
            conn.commit()
            return True
    except Exception as e:
        print(f"Database error (add_redemption_record): {e}")
        return False

def has_redeemed(player_id, gift_code):
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 1 FROM redemption_history
                WHERE player_id = ? AND gift_code = ?
            """, (player_id, gift_code))
            return cursor.fetchone() is not None
    except Exception as e:
        print(f"Database error (has_redeemed): {e}")
        return False

def add_active_code(gift_code):
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR IGNORE INTO active_gift_codes (gift_code)
                VALUES (?)
            """, (gift_code,))
            conn.commit()
            return True
    except Exception as e:
        print(f"Database error (add_active_code): {e}")
        return False

def get_active_codes():
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT gift_code FROM active_gift_codes")
            return [row[0] for row in cursor.fetchall()]
    except Exception as e:
        print(f"Database error (get_active_codes): {e}")
        return []
