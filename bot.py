import os
import discord
from discord import app_commands
from discord.ext import tasks, commands
from dotenv import load_dotenv

load_dotenv()

import asyncio
from datetime import datetime, timezone
import logging
import database
import giphy_client

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler()
    ]
)


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
        now = datetime.now(timezone.utc)
        current_time_str = now.strftime("%H:%M")
        current_date_str = now.strftime("%Y-%m-%d")
        
        reminders = database.get_reminders()
        # id, event_name, target_time, channel_id, gif_url, recurrence, target_date
        for rid, event_name, target_time, channel_id, gif_url, recurrence, target_date in reminders:
            should_send = False
            
            if recurrence == 'daily':
                if target_time == current_time_str:
                    should_send = True
            
            elif recurrence == 'once':
                if target_time == current_time_str and target_date == current_date_str:
                    should_send = True
                    # Schedule deletion after sending
                    asyncio.create_task(self.delete_reminder_later(rid))
            
            elif recurrence == 'weekly':
                # Check if today matches the target weekday
                if target_time == current_time_str:
                    target_dt = datetime.strptime(target_date, "%Y-%m-%d")
                    if now.weekday() == target_dt.weekday():
                        should_send = True

            elif recurrence == 'monthly':
                # Check if today matches the target day of month
                if target_time == current_time_str:
                    target_dt = datetime.strptime(target_date, "%Y-%m-%d")
                    if now.day == target_dt.day:
                        should_send = True

            if should_send:
                channel = self.get_channel(channel_id)
                if channel:
                    logging.info(f"Sending reminder for {event_name}")
                    embed = discord.Embed(description=f"~ {event_name}")
                    # Use specific GIF if available, otherwise default
                    final_gif = gif_url if gif_url else REMINDER_GIF_URL
                    embed.set_image(url=final_gif)
                    match recurrence:
                        case 'once': footer = "One-time reminder"
                        case 'daily': footer = "Daily reminder"
                        case 'weekly': footer = "Weekly reminder"
                        case 'monthly': footer = "Monthly reminder"
                        case _: footer = "Reminder"
                    embed.set_footer(text=footer)
                    await channel.send(content="@everyone", embed=embed, allowed_mentions=discord.AllowedMentions.all())

    async def delete_reminder_later(self, rid):
        await asyncio.sleep(5) # Wait a bit ensures message sends
        database.delete_reminder(rid)
        logging.info(f"Deleted one-time reminder ID {rid}")

    @check_reminders.before_loop
    async def before_check_reminders(self):
        await self.wait_until_ready()

bot = ReminderBot()

def is_authorized():
    async def predicate(interaction: discord.Interaction):
        # Check for Administrator permission
        if interaction.user.guild_permissions.administrator:
            logging.info(f"Authorized access for {interaction.user} (ID: {interaction.user.id}) via ADMIN privileges.")
            return True
            
        # Check for Authorized Roles
        for role_id in AUTHORIZED_ROLE_IDS:
            role = discord.utils.get(interaction.user.roles, id=role_id)
            if role:
                logging.info(f"Authorized access for {interaction.user} (ID: {interaction.user.id}) via ROLE match (Role ID: {role_id}).")
                return True
                
        # Access Denied
        logging.warning(f"Unauthorized access attempt by {interaction.user} (ID: {interaction.user.id}). Missing Admin or Role.")
        await interaction.response.send_message("You do not have the required role to use this command.", ephemeral=True)
        return False
    return app_commands.check(predicate)

class GifSelect(discord.ui.Select):
    def __init__(self, gifs):
        self.gifs = gifs # List of (url, title)
        options = [
            discord.SelectOption(label=title[:100], value=str(index)) 
            for index, (url, title) in enumerate(gifs)
        ]
        super().__init__(placeholder="Select a GIF to preview...", options=options)

    async def callback(self, interaction: discord.Interaction):
        # Update the image in the embed to the selected GIF
        selected_index = int(self.values[0])
        selected_url, selected_title = self.gifs[selected_index]
        
        embed = interaction.message.embeds[0]
        embed.set_image(url=selected_url)
        embed.set_footer(text=f"Selected: {selected_title}")
        
        # Update the view so the confirm button knows the current selection
        self.view.selected_url = selected_url
        await interaction.response.edit_message(embed=embed, view=self.view)

class GifSelectionView(discord.ui.View):
    def __init__(self, gifs, guild_id, event_name, target_time, channel_id, user_id, recurrence, target_date):
        super().__init__()
        self.selected_url = gifs[0][0] # Default to first result
        self.guild_id = guild_id
        self.event_name = event_name
        self.target_time = target_time
        self.channel_id = channel_id
        self.user_id = user_id
        self.recurrence = recurrence
        self.target_date = target_date
        
        self.add_item(GifSelect(gifs))

    @discord.ui.button(label="Confirm Selection", style=discord.ButtonStyle.success)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        success = database.add_reminder(
            self.guild_id,
            self.event_name,
            self.target_time,
            self.channel_id,
            self.user_id,
            self.selected_url,
            self.recurrence,
            self.target_date
        )
        
        if success:
            logging.info(f"User {self.user_id} created reminder with GIF")
            await interaction.response.edit_message(content=f"Reminder set for **{self.event_name}** at **{self.target_time}** ({self.recurrence})!", view=None, embed=None)
        else:
            await interaction.response.edit_message(content="Failed to save reminder.", view=None)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="Reminder Setup Cancelled.", view=None, embed=None)

class ReminderModal(discord.ui.Modal, title='Setup Reminder'):
    event_name = discord.ui.TextInput(label='Event Name', placeholder='e.g., Arena Time')
    target_time = discord.ui.TextInput(label='Time (HH:MM UTC)', placeholder='e.g., 23:55', min_length=5, max_length=5)

    def __init__(self, guild_id, channel_id, recurrence):
        super().__init__()
        self.guild_id = guild_id
        self.channel_id = channel_id
        self.recurrence = recurrence
        
        # Dynamic Target Date Input (Only for non-daily)
        if recurrence != 'daily':
            date_label = f"Date (YYYY-MM-DD) for {recurrence.capitalize()}"
            self.target_date = discord.ui.TextInput(
                label=date_label, 
                placeholder='e.g., 2023-12-25', 
                min_length=10, 
                max_length=10, 
                required=True
            )
            self.add_item(self.target_date)

        # Search Term Input (Added last)
        self.search_term = discord.ui.TextInput(
            label='GIF Theme (Optional)', 
            placeholder='e.g., cats, matrix, victory', 
            required=False
        )
        self.add_item(self.search_term)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            # Validate time format
            datetime.strptime(self.target_time.value, "%H:%M")
            
            date_val = None
            if self.recurrence != 'daily':
                # Check for the attribute first, just in case
                if hasattr(self, 'target_date'):
                    date_val = self.target_date.value
                    try:
                        datetime.strptime(date_val, "%Y-%m-%d")
                    except ValueError:
                        await interaction.response.send_message('Invalid date format. Please use YYYY-MM-DD.', ephemeral=True)
                        return
            
            # Defer response since Giphy API might take a moment
            await interaction.response.defer(ephemeral=True)
            
            search_query = self.search_term.value or "reminder"
            gifs = await giphy_client.search_gifs(search_query)
            
            if not gifs:
                await interaction.followup.send("No GIFs found for that term. Please try again.", ephemeral=True)
                return

            # Show preview UI
            embed = discord.Embed(title="Select a GIF", description=f"Results for '{search_query}'")
            embed.set_image(url=gifs[0][0]) # Show first result
            embed.set_footer(text=f"Selected: {gifs[0][1]}")
            
            view = GifSelectionView(
                gifs, 
                self.guild_id, 
                self.event_name.value, 
                self.target_time.value, 
                self.channel_id, 
                interaction.user.id,
                self.recurrence,
                date_val
            )
            
            await interaction.followup.send(embed=embed, view=view, ephemeral=True)

        except ValueError:
            await interaction.response.send_message('Invalid time format. Please use HH:MM (24-hour).', ephemeral=True)

class FrequencySelect(discord.ui.Select):
    def __init__(self, guild_id, channel_id):
        options = [
            discord.SelectOption(label="Daily", description="Repeats every day at the specified time", value="daily", emoji="🔁"),
            discord.SelectOption(label="Weekly", description="Repeats on this day every week", value="weekly", emoji="📅"),
            discord.SelectOption(label="Monthly", description="Repeats on this date every month", value="monthly", emoji="📆"),
            discord.SelectOption(label="One-time", description="Remind once then auto-delete", value="once", emoji="1️⃣"),
        ]
        super().__init__(placeholder="How often should this repeat?", options=options)
        self.guild_id = guild_id
        self.channel_id = channel_id

    async def callback(self, interaction: discord.Interaction):
        modal = ReminderModal(self.guild_id, self.channel_id, self.values[0])
        await interaction.response.send_modal(modal)

class FrequencyView(discord.ui.View):
    def __init__(self, guild_id, channel_id):
        super().__init__()
        self.add_item(FrequencySelect(guild_id, channel_id))

class ChannelSelect(discord.ui.Select):
    def __init__(self, channels):
        options = [
            discord.SelectOption(label=f"#{c.name}", value=str(c.id)) 
            for c in channels[:25] # Discord limits selects to 25 items
        ]
        super().__init__(placeholder="Choose a channel for the reminder...", options=options)

    async def callback(self, interaction: discord.Interaction):
        # Proceed to Frequency Select instead of Modal directly
        view = FrequencyView(interaction.guild_id, int(self.values[0]))
        await interaction.response.send_message("Select recurrence frequency:", view=view, ephemeral=True)

class ChannelSelectView(discord.ui.View):
    def __init__(self, channels):
        super().__init__()
        self.add_item(ChannelSelect(channels))

@bot.tree.command(name="remind-setup", description="Setup a recurring daily reminder")
@is_authorized()
async def remind_setup(interaction: discord.Interaction):
    logging.info(f"User {interaction.user} (ID: {interaction.user.id}) initiated /remind-setup in guild {interaction.guild_id}")
    
    # Get all text channels the bot can send messages to
    channels = [
        c for c in interaction.guild.text_channels 
        if c.permissions_for(interaction.guild.me).send_messages
    ]
    
    if not channels:
        await interaction.response.send_message("I don't have permission to send messages in any channels!", ephemeral=True)
        return

    # If only one channel, skip selection and go to frequency
    if len(channels) == 1:
        view = FrequencyView(interaction.guild_id, channels[0].id)
        await interaction.response.send_message("Select recurrence frequency:", view=view, ephemeral=True)
    else:
        view = ChannelSelectView(channels)
        await interaction.response.send_message("Select which channel this reminder should be sent to:", view=view, ephemeral=True)

class EditReminderModal(discord.ui.Modal, title='Edit Reminder'):
    def __init__(self, reminder_id, current_name, current_time):
        super().__init__()
        self.reminder_id = reminder_id
        self.event_name = discord.ui.TextInput(label='Event Name', default=current_name)
        self.target_time = discord.ui.TextInput(label='Time (HH:MM UTC)', default=current_time, min_length=5, max_length=5)
        self.add_item(self.event_name)
        self.add_item(self.target_time)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            datetime.strptime(self.target_time.value, "%H:%M")
            success = database.update_reminder(self.reminder_id, self.event_name.value, self.target_time.value)
            if success:
                logging.info(f"User {interaction.user} (ID: {interaction.user.id}) updated reminder ID {self.reminder_id} to: '{self.event_name.value}' at {self.target_time.value} UTC")
                await interaction.response.send_message(f'Updated **{self.event_name.value}** to **{self.target_time.value} UTC**.', ephemeral=True)
            else:
                logging.error(f"Failed to update reminder ID {self.reminder_id} for {interaction.user}")
                await interaction.response.send_message('Failed to update reminder.', ephemeral=True)
        except ValueError:
            logging.warning(f"User {interaction.user} provided invalid time format during edit: {self.target_time.value}")
            await interaction.response.send_message('Invalid time format. Please use HH:MM (24-hour).', ephemeral=True)

class EditSelect(discord.ui.Select):
    def __init__(self, reminders):
        options = [
            discord.SelectOption(label=f"{name} ({time} UTC)", value=str(rid)) 
            for rid, name, time, _, _, _, _ in reminders
        ]
        super().__init__(placeholder="Select a reminder to manage...", options=options)
        self.reminders = {str(rid): (name, time) for rid, name, time, _, _, _, _ in reminders}

    async def callback(self, interaction: discord.Interaction):
        reminder_id = int(self.values[0])
        name, time = self.reminders[self.values[0]]
        
        view = discord.ui.View()
        
        # Edit Button
        edit_btn = discord.ui.Button(label="Edit Details", style=discord.ButtonStyle.primary)
        async def edit_callback(itn: discord.Interaction):
            await itn.response.send_modal(EditReminderModal(reminder_id, name, time))
        edit_btn.callback = edit_callback
        
        # Delete Button
        delete_btn = discord.ui.Button(label="Delete", style=discord.ButtonStyle.danger)
        async def delete_callback(itn: discord.Interaction):
            database.delete_reminder(reminder_id)
            logging.info(f"User {itn.user} (ID: {itn.user.id}) deleted reminder: '{name}'")
            await itn.response.send_message(f"Deleted reminder: **{name}**", ephemeral=True)
        delete_btn.callback = delete_callback
        
        view.add_item(edit_btn)
        view.add_item(delete_btn)
        
        await interaction.response.send_message(f"Managing: **{name}** ({time} UTC)", view=view, ephemeral=True)

class EditView(discord.ui.View):
    def __init__(self, reminders):
        super().__init__()
        self.add_item(EditSelect(reminders))

@bot.tree.command(name="remind-edit", description="View and manage active reminders")
@is_authorized()
async def remind_edit(interaction: discord.Interaction):
    logging.info(f"User {interaction.user} (ID: {interaction.user.id}) initiated /remind-edit in guild {interaction.guild_id}")
    reminders = database.get_all_reminders_full(interaction.guild_id)
    if not reminders:
        await interaction.response.send_message("No active reminders found for this server.", ephemeral=True)
        return
    
    view = EditView(reminders)
    await interaction.response.send_message("Choose a reminder to edit or delete:", view=view, ephemeral=True)

if __name__ == "__main__":
    if not TOKEN or TOKEN == "your_bot_token_here":
        logging.error("DISCORD_TOKEN not set in .env")
    else:
        bot.run(TOKEN)
