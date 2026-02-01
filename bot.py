import os
import discord
from discord import app_commands
from discord.ext import tasks, commands
from dotenv import load_dotenv
import asyncio
from datetime import datetime
import logging
import database

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler()
    ]
)

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
AUTHORIZED_ROLE_IDS = [int(x.strip()) for x in os.getenv("AUTHORIZED_ROLE_ID", "").split(",") if x.strip()]
DEFAULT_CHANNEL_IDS = [int(x.strip()) for x in os.getenv("DEFAULT_CHANNEL_ID", "").split(",") if x.strip()]
REMINDER_GIF_URL = os.getenv("REMINDER_GIF_URL")

class ReminderBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        database.init_db()
        self.check_reminders.start()
        logging.info("Database initialized and scheduler started.")

    async def on_ready(self):
        logging.info(f'Logged in as {self.user} (ID: {self.user.id})')
        try:
            synced = await self.tree.sync()
            logging.info(f"Synced {len(synced)} command(s)")
        except Exception as e:
            logging.error(f"Failed to sync commands: {e}")

    @tasks.loop(seconds=60)
    async def check_reminders(self):
        now = datetime.now().strftime("%H:%M")
        reminders = database.get_reminders()
        for event_name, target_time, channel_id in reminders:
            if target_time == now:
                channel = self.get_channel(channel_id)
                if channel:
                    embed = discord.Embed(description=f"~ {event_name}")
                    embed.set_image(url=REMINDER_GIF_URL)
                    await channel.send(content="@everyone", embed=embed, allowed_mentions=discord.AllowedMentions.all())

    @check_reminders.before_loop
    async def before_check_reminders(self):
        await self.wait_until_ready()

bot = ReminderBot()

def is_authorized():
    async def predicate(interaction: discord.Interaction):
        if interaction.user.guild_permissions.administrator:
            return True
        for role_id in AUTHORIZED_ROLE_IDS:
            role = discord.utils.get(interaction.user.roles, id=role_id)
            if role:
                return True
        await interaction.response.send_message("You do not have the required role to use this command.", ephemeral=True)
        return False
    return app_commands.check(predicate)

class ReminderModal(discord.ui.Modal, title='Setup Reminder'):
    event_name = discord.ui.TextInput(label='Event Name', placeholder='e.g., Arena Time')
    target_time = discord.ui.TextInput(label='Time (HH:MM)', placeholder='e.g., 23:55', min_length=5, max_length=5)

    def __init__(self, channel_id):
        super().__init__()
        self.channel_id = channel_id

    async def on_submit(self, interaction: discord.Interaction):
        try:
            # Validate time format
            datetime.strptime(self.target_time.value, "%H:%M")
            success = database.add_reminder(
                self.event_name.value,
                self.target_time.value,
                self.channel_id,
                interaction.user.id
            )
            if success:
                await interaction.response.send_message(f'Reminder set for **{self.event_name.value}** at **{self.target_time.value}**.', ephemeral=True)
            else:
                await interaction.response.send_message('Failed to save reminder to database.', ephemeral=True)
        except ValueError:
            await interaction.response.send_message('Invalid time format. Please use HH:MM (24-hour).', ephemeral=True)

class ChannelSelect(discord.ui.Select):
    def __init__(self, channels):
        options = [
            discord.SelectOption(label=f"#{c.name}", value=str(c.id)) 
            for c in channels if c
        ]
        super().__init__(placeholder="Choose a channel for the reminder...", options=options)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(ReminderModal(int(self.values[0])))

class ChannelSelectView(discord.ui.View):
    def __init__(self, channels):
        super().__init__()
        self.add_item(ChannelSelect(channels))

@bot.tree.command(name="remind-setup", description="Setup a recurring daily reminder")
@is_authorized()
async def remind_setup(interaction: discord.Interaction):
    if len(DEFAULT_CHANNEL_IDS) > 1:
        channels = [bot.get_channel(id) for id in DEFAULT_CHANNEL_IDS]
        await interaction.response.send_message("Select which channel this reminder should be sent to:", view=ChannelSelectView(channels), ephemeral=True)
    elif len(DEFAULT_CHANNEL_IDS) == 1:
        await interaction.response.send_modal(ReminderModal(DEFAULT_CHANNEL_IDS[0]))
    else:
        await interaction.response.send_message("No default channels configured in .env", ephemeral=True)

class EditView(discord.ui.View):
    def __init__(self, reminders):
        super().__init__()
        self.reminders = reminders
        for rid, name, time, _ in reminders:
            self.add_item(EditButton(rid, name, time))

class EditButton(discord.ui.Button):
    def __init__(self, reminder_id, name, time):
        super().__init__(label=f"Delete {name} ({time})", style=discord.ButtonStyle.danger)
        self.reminder_id = reminder_id

    async def callback(self, interaction: discord.Interaction):
        database.delete_reminder(self.reminder_id)
        await interaction.response.send_message(f"Deleted reminder.", ephemeral=True)

@bot.tree.command(name="remind-edit", description="View and manage active reminders")
@is_authorized()
async def remind_edit(interaction: discord.Interaction):
    reminders = database.get_all_reminders_full()
    if not reminders:
        await interaction.response.send_message("No active reminders found.", ephemeral=True)
        return
    
    view = EditView(reminders)
    await interaction.response.send_message("Click a button to delete a reminder:", view=view, ephemeral=True)

if __name__ == "__main__":
    if not TOKEN or TOKEN == "your_bot_token_here":
        logging.error("DISCORD_TOKEN not set in .env")
    else:
        bot.run(TOKEN)
