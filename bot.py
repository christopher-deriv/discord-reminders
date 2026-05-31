import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
import asyncio
import logging
import database

load_dotenv()

# Configure logging
if not os.path.exists('logs'):
    os.makedirs('logs')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/bot.log"),
        logging.StreamHandler()
    ]
)

TOKEN = os.getenv("DISCORD_TOKEN")

class ReminderBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        # central SQLite initialization
        database.init_db()
        logging.info("SQLite database initialized.")

        # Dynamically load modular cogs
        cogs = ["cogs.reminder_cog", "cogs.translation_cog", "cogs.gift_cog"]
        for cog in cogs:
            try:
                await self.load_extension(cog)
                logging.info(f"Cog '{cog}' loaded successfully.")
            except Exception as e:
                logging.error(f"Failed to load cog '{cog}': {e}", exc_info=True)

        self.tree.on_error = self.on_tree_error
        logging.info("Command tree error handler registered.")

    async def on_tree_error(self, interaction: discord.Interaction, error: discord.app_commands.AppCommandError):
        if isinstance(error, discord.app_commands.CheckFailure):
            logging.warning(f"Command '{interaction.command.name}' blocked by authorization check.")
        else:
            logging.error(f"Ignoring exception in command '{interaction.command.name}':", exc_info=error)

    async def on_ready(self):
        logging.info(f'Logged in as {self.user} (ID: {self.user.id})')
        try:
            synced = await self.tree.sync()
            logging.info(f"Synced {len(synced)} command(s)")
        except discord.HTTPException as e:
            if "50240" in str(e):
                logging.warning(f"Skipping command sync: {e} (Normal if an Activity Entry Point exists in the portal)")
            else:
                logging.error(f"Failed to sync commands: {e}")
        except Exception as e:
            logging.error(f"Failed to sync commands: {e}")

bot = ReminderBot()

async def main():
    if not TOKEN or TOKEN == "your_bot_token_here":
        logging.error("DISCORD_TOKEN not set in .env")
        return

    await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
