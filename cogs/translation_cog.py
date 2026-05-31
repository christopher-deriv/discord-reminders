import os
import discord
from discord.ext import commands
import logging
from collections import deque
import asyncio

try:
    from google.cloud import translate_v2 as translate
except ImportError:
    translate = None

FLAG_LANG_MAP = {
    "🇺🇸": "en", "🇬🇧": "en",
    "🇪🇸": "es", "🇫🇷": "fr", "🇩🇪": "de", "🇮🇹": "it", "🇵🇹": "pt",
    "🇨🇳": "zh-CN", "🇹🇼": "zh-TW", "🇯🇵": "ja", "🇰🇷": "ko", "🇮🇳": "hi",
    "🇧🇩": "bn", "🇹🇭": "th", "🇻🇳": "vi", "🇮🇩": "id", "🇲🇾": "ms",
    "🇷🇺": "ru", "🇳🇱": "nl", "🇵🇱": "pl", "🇹🇷": "tr", "🇸🇪": "sv",
    "🇩🇰": "da", "🇳🇴": "no", "🇫🇮": "fi", "🇨🇿": "cs", "🇭🇺": "hu",
    "🇷🇴": "ro", "🇬🇷": "el", "🇺🇦": "uk", "🇸🇦": "ar", "🇮🇱": "he"
}

class TranslationCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.translated_messages = set()
        self.translated_messages_queue = deque(maxlen=1000)
        self.translate_client = None
        
        try:
            if translate:
                self.translate_client = translate.Client()
                logging.info("Google Cloud Translate client initialized successfully inside TranslationCog.")
            else:
                logging.warning("google-cloud-translate library is missing. Translation feature disabled.")
        except Exception as e:
            logging.warning(f"Google Cloud Translate client failed to initialize: {e}. Translation feature will not work.")

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        if not self.translate_client:
            return

        emoji_name = payload.emoji.name
        if emoji_name not in FLAG_LANG_MAP:
            return

        target_lang = FLAG_LANG_MAP[emoji_name]
        message_id = payload.message_id

        # Check cache to prevent translating the same message to the same language multiple times
        cache_key = (message_id, target_lang)
        if cache_key in self.translated_messages:
            return

        # Lock cache
        self.translated_messages.add(cache_key)
        self.translated_messages_queue.append(cache_key)

        # Cleanup old cache entries
        if len(self.translated_messages) > 1000:
            while len(self.translated_messages) > len(self.translated_messages_queue):
                self.translated_messages = set(self.translated_messages_queue)

        channel = self.bot.get_channel(payload.channel_id)
        if not channel:
            return

        try:
            message = await channel.fetch_message(message_id)
        except (discord.NotFound, discord.Forbidden):
            return

        # Ignore messages from bots and empty messages
        if message.author.bot or not message.content:
            return

        # Perform the translation call
        try:
            # Use asyncio.to_thread to prevent blocking the event loop with GCP API call
            result = await asyncio.to_thread(
                self.translate_client.translate,
                message.content,
                target_language=target_lang,
                format_="text"
            )
            translated_text = result["translatedText"]

            # Send reply
            await message.reply(content=translated_text, allowed_mentions=discord.AllowedMentions.none())
            logging.info(f"Translated message {message_id} to {target_lang}")
        except Exception as e:
            # Revert cache lock if translation failed
            self.translated_messages.discard(cache_key)
            logging.error(f"Failed to translate message {message_id}: {e}")

async def setup(bot):
    await bot.add_cog(TranslationCog(bot))
