import sys
import os
import logging

# Ensure root directory is in sys.path
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

logging.basicConfig(level=logging.INFO)

print("[*] Starting compilation and import checks...")

try:
    print("[1/5] Importing database.py...")
    import database
    database.init_db()
    print("      SUCCESS: database.py imported and initialized successfully.")
except Exception as e:
    print(f"      ERROR: Failed to import database.py: {e}")
    sys.exit(1)

try:
    print("[2/5] Importing kingshot_client.py...")
    import kingshot_client
    # Let's instantiate the client and print solver status
    client = kingshot_client.KingShotClient()
    print(f"      SUCCESS: kingshot_client.py imported. ML Solver enabled: {client.solver.enabled}")
except Exception as e:
    print(f"      ERROR: Failed to import kingshot_client.py: {e}")
    sys.exit(1)

try:
    print("[3/5] Importing cogs/reminder_cog.py...")
    from cogs import reminder_cog
    print("      SUCCESS: cogs/reminder_cog.py imported successfully.")
except Exception as e:
    print(f"      ERROR: Failed to import cogs/reminder_cog.py: {e}")
    sys.exit(1)

try:
    print("[4/5] Importing cogs/translation_cog.py...")
    from cogs import translation_cog
    print("      SUCCESS: cogs/translation_cog.py imported successfully.")
except Exception as e:
    print(f"      ERROR: Failed to import cogs/translation_cog.py: {e}")
    sys.exit(1)

try:
    print("[5/5] Importing cogs/gift_cog.py...")
    from cogs import gift_cog
    print("      SUCCESS: cogs/gift_cog.py imported successfully.")
except Exception as e:
    print(f"      ERROR: Failed to import cogs/gift_cog.py: {e}")
    sys.exit(1)

print("\n[+] ALL CODE COMPILED AND IMPORTED SUCCESSFUL!")
