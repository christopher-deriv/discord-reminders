# Discord Event Reminder Bot

A containerized Discord bot that allows authorized users to schedule recurring reminders (Daily, Weekly, Monthly, or One-time) with integrated Giphy support.

## 🚀 Features

- **Advanced Scheduling**:
    - **Daily**: Repeats every day at a specific time.
    - **Weekly**: Repeats on a specific day of the week.
    - **Monthly**: Repeats on a specific day of the month.
    - **One-time**: Fires once and automatically deletes itself.
- **Visuals**: Search and attach GIFs from Giphy directly within the setup flow.
- **Slash Commands**: `/remind-setup` and `/remind-edit`.
- **Interactive UI**:
    - Wizard-style setup (Channel -> Frequency -> Details -> GIF).
    - Dynamic Modals (Date field hides for Daily reminders).
    - Select Menus for managing existing reminders.
- **Privacy & Security**:
    - Reminders are isolated per-server (Guild).
    - Role-based access control.
- **Containerized**: Ready for 24/7 deployment using Docker.

## 🛠 Prerequisites

- [Docker](https://www.docker.com/) and Docker Compose.
- A Discord Bot Token (from [Discord Developer Portal](https://discord.com/developers/applications)).
- A Giphy API Key (from [Giphy Developers](https://developers.giphy.com/)).
- Developer Mode enabled in Discord to copy IDs.

## ⚙️ Setup & Configuration

1. **Clone the repository** to your server.
2. **Create a `.env` file** based on the template:

   ```env
   DISCORD_TOKEN=your_bot_token_here
   AUTHORIZED_ROLE_ID=role_id_1,role_id_2
   GIPHY_API_KEY=your_giphy_api_key_here
   # Optional fallback
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

### `/remind-setup`
Starts the interactive setup wizard:
1.  **Channel Selection**: Choose where the reminder should be sent (if applicable).
2.  **Frequency**: Select Daily, Weekly, Monthly, or One-time.
3.  **Details**: Enter Event Name, Time (UTC), and Date (if not Daily).
4.  **GIF Theme**: Search for a GIF to attach to the reminder.

### `/remind-edit`
Displays a dropdown of active reminders to edit or delete them.

## 🔍 Troubleshooting

- **Check Logs**:
  ```bash
  docker-compose logs -f
  ```
- **Database**: The database is stored in the `./data` volume. If you experience schema errors after an update, delete `data/bot.db` and restart the bot to recreate it.

---

*Found a bug? Open an issue or submit a PR!*
