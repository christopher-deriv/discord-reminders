# Discord Event Reminder Bot

A containerized Discord bot that allows authorized users to schedule recurring daily reminders via a Modal interface.

## 🚀 Features

- **Slash Commands**: `/remind-setup` and `/remind-edit`.
- **Modal UI**: Easy-to-use form for setting event names and times (24h format).
- **Multiple IDs**: Support for multiple authorized roles and target channels.
- **Persistence**: Reminders are stored in a local SQLite database (`/data/bot.db`).
- **Containerized**: Ready for 24/7 deployment using Docker.
- **Logging**: Dual logging to console and local `.log` files.

## 🛠 Prerequisites

- [Docker](https://www.docker.com/) and Docker Compose.
- A Discord Bot Token (from [Discord Developer Portal](https://discord.com/developers/applications)).
- Developer Mode enabled in Discord to copy IDs.

## ⚙️ Setup & Configuration

1. **Clone the repository** to your server.
2. **Create a `.env` file** based on the template:

   ```env
   DISCORD_TOKEN=your_bot_token_here
   AUTHORIZED_ROLE_ID=role_id_1,role_id_2
   DEFAULT_CHANNEL_ID=channel_id_1,channel_id_2
   REMINDER_GIF_URL=https://media.giphy.com/media/.../giphy.gif
   ```

3. **Configure Permissions**: Ensure your bot has the following permissions:
   - `bot` and `applications.commands` (OAuth2 Scopes)
   - `View Channels`, `Send Messages`, `Embed Links`, `Mention @everyone`.

## 📦 Deployment

Run the bot in the background:

```bash
docker-compose up -d --build
```

## 📝 Commands

- `/remind-setup`: Opens a modal to create a new daily reminder. If multiple channels are configured, you will be prompted to select a target channel first.
- `/remind-edit`: Displays a list of active reminders with buttons to delete them.

## 🔍 Troubleshooting

- **Check Logs**:
  ```bash
  docker-compose logs -f
  ```
- **Local Logs**: Check `bot.log` or `reminder.log` in the project directory.
- **Database**: The database is stored in the `./data` volume to persist across container updates.

---

*Found a bug? Open an issue or submit a PR!*
