import unittest
import os
import sqlite3
import tempfile
import time
import database
import kingshot_client

class TestGiftRedemption(unittest.TestCase):
    def setUp(self):
        # Create a temporary database for test isolation
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.temp_db.close()
        self.orig_db_path = database.DB_PATH
        database.DB_PATH = self.temp_db.name
        database.init_db()

    def tearDown(self):
        database.DB_PATH = self.orig_db_path
        import gc
        gc.collect()
        try:
            if os.path.exists(self.temp_db.name):
                os.remove(self.temp_db.name)
        except Exception:
            pass

    def test_database_registration_with_kingdom(self):
        # Register a player with specific kingdom
        success = database.register_player(12345, 99999, "28633797", kingdom_id="104", player_name="TestHero")
        self.assertTrue(success)

        players = database.get_registered_players(12345, 99999)
        self.assertEqual(len(players), 1)
        pid, kid, name = players[0]
        self.assertEqual(pid, "28633797")
        self.assertEqual(kid, "104")
        self.assertEqual(name, "TestHero")

    def test_database_default_kingdom_backfill(self):
        # Register a player with default kingdom
        success = database.register_player(12345, 99999, "99999999")
        self.assertTrue(success)

        players = database.get_registered_players(12345, 99999)
        self.assertEqual(len(players), 1)
        pid, kid, name = players[0]
        self.assertEqual(pid, "99999999")
        self.assertEqual(kid, "141")

    def test_database_migration_backfill_existing_nulls(self):
        # Insert a raw record without kingdom_id
        with sqlite3.connect(database.DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT OR REPLACE INTO alliance_players (discord_id, guild_id, player_id, kingdom_id, player_name) VALUES (?, ?, ?, NULL, ?)",
                           (111, 222, "123456", "OldPlayer"))
            conn.commit()

        # Call init_db() which runs migration backfill
        database.init_db()

        players = database.get_registered_players(111, 222)
        self.assertEqual(len(players), 1)
        pid, kid, name = players[0]
        self.assertEqual(kid, "141")

    def test_signature_generation(self):
        client = kingshot_client.KingShotClient()
        data = {
            "fid": "28633797",
            "kid": "141",
            "cdk": "OFFICIALSTORE27",
            "time": "1725220000"
        }
        sig = client.generate_signature(data)
        self.assertTrue(isinstance(sig, str))
        self.assertEqual(len(sig), 32) # MD5 hex is 32 chars

if __name__ == '__main__':
    unittest.main()
