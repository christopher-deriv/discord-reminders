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

## 📖 User Guide

### 1️⃣ Setting a Reminder
Type `/remind-setup` and follow the interactive wizard:

1.  **Select Channel**: Choose the channel where the bot should post.
2.  **Select Frequency**:
    *   **Daily**: Repeating every day.
    *   **Weekly**: Repeating every week (on the day of the date provided).
    *   **Monthly**: Repeating every month (on the day of the date provided).
    *   **One-time**: Runs once and then auto-deletes.
3.  **Enter Details**:
    *   **Name**: Event title (e.g., "Raid Time").
    *   **Time**: 24-hour UTC format (e.g., `18:00`).
    *   **Date**: Required for non-daily events (Format: `YYYY-MM-DD`).
    *   **GIF Theme**: Keyword to search Giphy. **Leave blank** for no GIF.
4.  **GIF Selection**: If you entered a search term, pick your favorite GIF from the preview menu.

### 2️⃣ Managing Reminders
Type `/remind-edit` to manage active reminders:
*   Select a reminder from the dropdown list.
*   **Edit Details**: Update the event name or time.
*   **Delete**: Permanently remove the reminder.

## 🔍 Troubleshooting

- **Check Logs**:
  ```bash
  docker-compose logs -f
  ```
- **Database**: The database is stored in the `./data` volume. If you experience schema errors after an update, delete `data/bot.db` and restart the bot to recreate it.

---

*Found a bug? Open an issue or submit a PR!*
