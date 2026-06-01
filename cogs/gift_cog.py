import os
import asyncio
import discord
from discord import app_commands
from discord.ext import tasks, commands
import logging
import random
import database
import kingshot_client
import aiohttp

AUTHORIZED_ROLE_IDS = [int(x.strip()) for x in os.getenv("AUTHORIZED_ROLE_ID", "").split(",") if x.strip()]
GIFT_LOG_CHANNEL_ID = os.getenv("GIFT_LOG_CHANNEL_ID")

def is_authorized():
    async def predicate(interaction: discord.Interaction):
        if interaction.user.guild_permissions.administrator:
            logging.info(f"Authorized access for {interaction.user} (ID: {interaction.user.id}) via ADMIN privileges.")
            return True
            
        for role_id in AUTHORIZED_ROLE_IDS:
            role = discord.utils.get(interaction.user.roles, id=role_id)
            if role:
                logging.info(f"Authorized access for {interaction.user} (ID: {interaction.user.id}) via ROLE match (Role ID: {role_id}).")
                return True
                
        logging.warning(f"Unauthorized access attempt by {interaction.user} (ID: {interaction.user.id}). Missing Admin or Role.")
        await interaction.response.send_message("You do not have the required role to use this command.", ephemeral=True)
        return False
    return app_commands.check(predicate)

class GiftCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.poll_gift_codes.start()

    def cog_unload(self):
        self.poll_gift_codes.cancel()

    @tasks.loop(hours=2)
    async def poll_gift_codes(self):
        """
        Background task running every 2 hours to poll and auto-redeem active gift codes.
        """
        logging.info("Starting background gift code auto-redemption cycle...")
        
        # 1. Fetch active codes from DB and resiliently from public API
        active_codes = set(database.get_active_codes())
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get("https://kingshot.net/api/gift-codes", timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        if isinstance(data, list):
                            for item in data:
                                if isinstance(item, dict) and "code" in item:
                                    active_codes.add(item["code"].upper().strip())
                                elif isinstance(item, str):
                                    active_codes.add(item.upper().strip())
                        elif isinstance(data, dict) and "codes" in data:
                           for code in data["codes"]:
                               active_codes.add(code.upper().strip())
        except Exception as e:
            logging.warning(f"Resilient poll: Public API for gift codes failed ({e}). Relying solely on local DB codes.")

        if not active_codes:
            logging.info("No active gift codes to process in this cycle.")
            return

        # 2. Query all registered players from the SQLite database
        all_players = []
        try:
            # Query all registered players from alliance_players
            import sqlite3
            with sqlite3.connect(database.DB_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT discord_id, guild_id, player_id, player_name FROM alliance_players")
                all_players = cursor.fetchall()
        except Exception as e:
            logging.error(f"Failed to query players for background auto-redemption: {e}")
            return

        if not all_players:
            logging.info("No players registered in the database for auto-redemption.")
            return

        # Group players by guild to enable server-specific isolation and summary reports
        guild_players = {}
        for discord_id, guild_id, player_id, player_name in all_players:
            if guild_id not in guild_players:
                guild_players[guild_id] = []
            guild_players[guild_id].append((discord_id, player_id, player_name))

        # 3. Process each guild sequentially
        async with kingshot_client.KingShotClient() as client:
            for guild_id, players in guild_players.items():
                guild = self.bot.get_guild(guild_id)
                if not guild:
                    continue

                success_count = 0
                failure_count = 0
                rate_limited = False
                redemptions_attempted = False

                for p_idx, (discord_id, player_id, player_name) in enumerate(players):
                    # Filter codes that this specific player has not yet redeemed
                    unclaimed_codes = [code for code in active_codes if not database.has_redeemed(player_id, code)]
                    if not unclaimed_codes:
                        continue

                    # Apply player-transition delay if transitioning between accounts
                    if redemptions_attempted:
                        delay = random.uniform(5.0, 10.0)
                        logging.info(f"Anti-flag: Waiting {delay:.2f}s before processing player {player_id}...")
                        await asyncio.sleep(delay)

                    redemptions_attempted = True
                    player_failed = False

                    # Always verify/login the player first to establish the API session
                    verify_res = await client.verify_player(player_id)
                    if verify_res.get("code") != 0:
                        logging.warning(f"Verify/Login failed for player {player_id}: {verify_res.get('msg')}")
                        failure_count += len(unclaimed_codes)
                        continue

                    for c_idx, code in enumerate(unclaimed_codes):
                        # Apply inter-code delay between individual code attempts for the same player
                        if c_idx > 0:
                            delay = random.uniform(2.0, 5.0)
                            await asyncio.sleep(delay)

                        logging.info(f"Auto-redeem: Code '{code}' for player '{player_name}' ({player_id})")
                        
                        res = await client.redeem_with_captcha_solver(player_id, code)
                        res_code = res.get("code")
                        err_code = res.get("err_code")
                        
                        if res_code == 429:
                            rate_limited = True
                            player_failed = True
                            break # Abort codes loop for this player
                            
                        # Century Games returns code=0 for success, code=1 with err_code=40008 for already claimed
                        is_success = (res_code == 0)
                        is_already_claimed = (res_code == 1 and err_code == 40008)

                        if is_success or is_already_claimed:
                            success_count += 1
                            database.add_redemption_record(player_id, code)
                        else:
                            failure_count += 1
                            player_failed = True
                            logging.warning(f"Redemption failed: {res.get('msg')} for player {player_id}")

                    if rate_limited:
                        logging.error("IP rate limit hit. Aborting background redemption queue for this cycle.")
                        break # Abort players loop for this guild

                    # If this specific player failed, we skip their other attempts and move to the next player
                    if player_failed:
                        logging.info(f"Skipping further attempts for player {player_id} due to failure/captcha.")
                        continue

                # 4. Consolidated Reporting for this guild
                if redemptions_attempted:
                    await self.post_summary_report(guild_id, len(active_codes), len(players), success_count, failure_count, rate_limited)

    async def post_summary_report(self, guild_id, total_codes, total_players, success_count, failure_count, rate_limited):
        """
        Sends a single, consolidated summary report to the configured channel to prevent spam.
        """
        guild = self.bot.get_guild(guild_id)
        if not guild:
            return

        # Locate target logging channel
        target_channel = None
        if GIFT_LOG_CHANNEL_ID:
            target_channel = guild.get_channel(int(GIFT_LOG_CHANNEL_ID))
            
        if not target_channel:
            # Fall back to first text channel where bot has send permissions
            for c in guild.text_channels:
                if c.permissions_for(guild.me).send_messages:
                    target_channel = c
                    break

        if not target_channel:
            logging.warning(f"Could not find a valid text channel to post redemption report in guild {guild_id}")
            return

        embed = discord.Embed(
            title="📊 KingShot Auto-Redemption Report",
            color=discord.Color.blue() if not rate_limited else discord.Color.red(),
            timestamp=discord.utils.utcnow()
        )
        embed.add_field(name="Active Codes", value=str(total_codes), inline=True)
        embed.add_field(name="Registered Players", value=str(total_players), inline=True)
        embed.add_field(name="Successes (Claimed)", value=f"✅ {success_count}", inline=True)
        embed.add_field(name="Failed / Skipped", value=f"❌ {failure_count}", inline=True)
        embed.add_field(name="Rate Limited (HTTP 429)", value="⚠️ Yes (Aborted)" if rate_limited else "No", inline=True)
        embed.set_footer(text="Failed accounts will be retried automatically in the next background cycle.")

        try:
            await target_channel.send(embed=embed)
        except Exception as e:
            logging.error(f"Failed to send consolidated report: {e}")

    @poll_gift_codes.before_loop
    async def before_poll_gift_codes(self):
        await self.bot.wait_until_ready()

    @app_commands.command(name="register", description="Register a KingShot Player ID")
    async def register(self, interaction: discord.Interaction, player_id: str):
        logging.info(f"User {interaction.user} (ID: {interaction.user.id}) initiated /register with Player ID {player_id}")
        await interaction.response.defer(ephemeral=True)

        async with kingshot_client.KingShotClient() as client:
            res = await client.verify_player(player_id)
            
            if res.get("code") != 0 or not res.get("data"):
                msg = res.get("msg", "Player verification failed")
                await interaction.followup.send(f"[-] Registration failed: {msg}.", ephemeral=True)
                return

            player_data = res["data"]
            nickname = player_data.get("nickname", "Unknown")
            kid = player_data.get("kid", "N/A")
            success = database.register_player(interaction.user.id, interaction.guild_id, player_id, nickname)
            if success:
                await interaction.followup.send(
                    f"[+] Player ID **{player_id}** successfully registered!\n"
                    f"* Nickname: **{nickname}**\n"
                    f"* Kingdom: **#{kid}**",
                    ephemeral=True
                )
            else:
                await interaction.followup.send("[-] Registration failed: Database write error.", ephemeral=True)

    @app_commands.command(name="unregister", description="Unregister a KingShot Player ID")
    async def unregister(self, interaction: discord.Interaction, player_id: str):
        logging.info(f"User {interaction.user} (ID: {interaction.user.id}) initiated /unregister with Player ID {player_id}")
        
        success = database.unregister_player(interaction.user.id, interaction.guild_id, player_id)
        if success:
            await interaction.response.send_message(f"[+] Player ID **{player_id}** successfully unregistered.", ephemeral=True)
        else:
            await interaction.response.send_message("[-] Unregistration failed: Database error.", ephemeral=True)

    @app_commands.command(name="my-players", description="List your registered KingShot Player IDs")
    async def my_players(self, interaction: discord.Interaction):
        logging.info(f"User {interaction.user} (ID: {interaction.user.id}) initiated /my-players")
        
        players = database.get_registered_players(interaction.user.id, interaction.guild_id)
        if not players:
            await interaction.response.send_message("You have no registered players in this guild.", ephemeral=True)
            return

        player_list = "\n".join([f"• **{name}** (ID: `{pid}`)" for pid, name in players])
        await interaction.response.send_message(f"### Your Registered KingShot Players:\n{player_list}", ephemeral=True)

    @app_commands.command(name="add-gift-code", description="Register a gift code for automated polling and redemption")
    @is_authorized()
    async def add_gift_code(self, interaction: discord.Interaction, gift_code: str):
        code_clean = gift_code.upper().strip()
        logging.info(f"User {interaction.user} (ID: {interaction.user.id}) initiated /add-gift-code with code {code_clean}")
        
        success = database.add_active_code(code_clean)
        if success:
            await interaction.response.send_message(f"[+] Gift code **{code_clean}** successfully registered for automated polling.", ephemeral=True)
        else:
            await interaction.response.send_message("[-] Failed to register gift code.", ephemeral=True)

    @app_commands.command(name="redeem-force", description="Force immediate redemption of a code for all players in this guild")
    @is_authorized()
    async def redeem_force(self, interaction: discord.Interaction, gift_code: str):
        code_clean = gift_code.upper().strip()
        logging.info(f"User {interaction.user} (ID: {interaction.user.id}) initiated /redeem-force for code {code_clean}")
        await interaction.response.defer(ephemeral=True)

        players = database.get_all_guild_players(interaction.guild_id)
        if not players:
            await interaction.followup.send("No players are registered in this guild.", ephemeral=True)
            return

        success_count = 0
        failure_count = 0
        rate_limited = False
        redemptions_attempted = False

        async with kingshot_client.KingShotClient() as client:
            for p_idx, (discord_id, player_id, player_name) in enumerate(players):
                # Skip if already redeemed
                if database.has_redeemed(player_id, code_clean):
                    continue

                # Apply player-transition delay if needed
                if redemptions_attempted:
                    delay = random.uniform(5.0, 10.0)
                    await asyncio.sleep(delay)

                redemptions_attempted = True

                # Always verify/login the player first to establish the API session
                verify_res = await client.verify_player(player_id)
                if verify_res.get("code") != 0:
                    logging.warning(f"Verify/Login failed for player {player_id}: {verify_res.get('msg')}")
                    failure_count += 1
                    continue

                res = await client.redeem_with_captcha_solver(player_id, code_clean)
                res_code = res.get("code")
                err_code = res.get("err_code")

                if res_code == 429:
                    rate_limited = True
                    break

                is_success = (res_code == 0)
                is_already_claimed = (res_code == 1 and err_code == 40008)

                if is_success or is_already_claimed:
                    success_count += 1
                    database.add_redemption_record(player_id, code_clean)
                else:
                    failure_count += 1
                    logging.warning(f"Force redeem failed: {res.get('msg')} for player {player_id}")

        # Final reporting
        if rate_limited:
            await interaction.followup.send(
                f"[-] Force redemption aborted: IP Rate Limited.\n"
                f"* Successes/Already Claimed: **{success_count}**\n"
                f"* Failures/Skipped: **{failure_count}**",
                ephemeral=True
            )
        elif not redemptions_attempted:
            await interaction.followup.send(f"[!] Code **{code_clean}** has already been redeemed for all registered players.", ephemeral=True)
        else:
            await interaction.followup.send(
                f"[+] Force redemption completed for code **{code_clean}**:\n"
                f"* Successes/Already Claimed: **{success_count}**\n"
                f"* Failures/Skipped (CAPTCHA/Error): **{failure_count}**",
                ephemeral=True
            )

async def setup(bot):
    await bot.add_cog(GiftCog(bot))
