# KingShot Gift Code Redeemer

A reverse-engineered, multi-account automation script for verifying players and redeeming gift codes on the official **KingShot** (`ks-giftcode.centurygame.com`) portal.

This project replicates the official web redemption flow, implementing player verification, cryptographic request signing, and automatic anti-flagging randomized delays.

---

## Technical Details (API Reverse-Engineered)

Through network analysis of the HTTP Archive (HAR) and static analysis of the dynamically-loaded home page chunk bundle (`/js/src_pages_home_index_vue.f36f48fd08f04273.js`), the underlying API mechanisms were mapped:

### 1. Endpoints
All requests are submitted as `POST` payloads with `application/x-www-form-urlencoded` encoding to `https://kingshot-giftcode.centurygame.com/api`:

* **Retrieve Config**: `/api/gift_code_config`
  * Payload: `time=<timestamp>&sign=<signature>`
* **Verify Player**: `/api/player`
  * Payload: `fid=<player_id>&time=<timestamp>&sign=<signature>`
* **Redeem Code**: `/api/gift_code`
  * Payload: `captcha_code=&cdk=<gift_code>&fid=<player_id>&time=<timestamp>&sign=<signature>`

### 2. Request Signing (`sign`)
To prevent unauthorized/automated requests, the server validates a cryptographic `sign` parameter. The client-side signature generation follows these rules:
1. Collect all parameters (excluding `sign`).
2. Sort the parameter keys **alphabetically**.
3. Format the sorted parameters as a standard URL query string (`key1=val1&key2=val2`).
4. Append the hardcoded secret salt string: **`mN4!pQs6JrYwV9`**.
5. Compute the **MD5 hash** of the final concatenated string.

#### Signature Formula Examples:
* **Config Check**: `time={timestamp}mN4!pQs6JrYwV9`
* **Player Lookup**: `fid={player_id}&time={timestamp}mN4!pQs6JrYwV9`
* **Redemption**: `captcha_code={captcha_code}&cdk={gift_code}&fid={player_id}&time={timestamp}mN4!pQs6JrYwV9`

---

## Features of the Redeemer Script

The [redeemer.py](redeemer.py) script is designed for safety, speed, and ease of use:

* **Automatic Anti-Flagging Delays**: Randomizes the sleep time between requests (default: `2.0` to `5.0` seconds) to break predictable bot patterns and prevent flagging/bans by anomaly-detection firewalls.
* **Multi-Account Queue**: Processes multiple Player IDs and multiple Gift Codes in a single run, verifying accounts and running redemptions sequentially.
* **Account Verification**: Queries and displays the player's Nickname, Kingdom, and Stove Level before attempting to redeem codes, ensuring Player IDs are valid.
* **Dual Operation Modes**: Works both in a command-line arguments mode and a simple interactive wizard.

---

## Installation & Requirements

The script is built using only standard Python libraries. No external dependencies (like `requests`) are needed.

* **Python Version**: Python 3.6 or higher.

---

## Usage

### 1. Interactive Mode
Run the script without arguments. The script will guide you and automatically apply the randomized `2-5` second delay in the background:
```bash
python redeemer.py
```
You will be prompted:
```text
Enter Player ID(s) (separated by commas or spaces): 129284382, 28633797
Enter Gift Code(s) (separated by commas or spaces): EIDALADHA0527, OFFICIALSTORE27
```

### 2. Command-Line Arguments Mode
Specify the Player IDs and Gift Codes directly. By default, this uses the automatic `2-5` second randomized delay:
```bash
python redeemer.py --ids "129284382,28633797" --codes "EIDALADHA0527,OFFICIALSTORE27"
```

#### Custom Delays (Optional)
If you wish to change the delay range or set a fixed delay, use the `--delay` flag:
* **Custom Range**: `--delay "3-8"` (Random pause between 3 and 8 seconds)
* **Fixed Delay**: `--delay "4.0"` (Fixed 4-second pause)
* **Instant**: `--delay "0"` (No pause)

---

## Discord Bot Integration Blueprint (Migration to `discord-reminders`)

This blueprint outlines how to migrate the core logic of `redeemer.py` to the sibling `discord-reminders` project as a Discord Cog, employing an automated, self-registered redemption workflow.

### 1. Database Schema Additions (`database.py`)
To manage players, automatic code polling, and prevent repeated redemption attempts, add two new tables to the SQLite database:

```sql
-- Track registered player IDs linked to Discord users (Option B)
CREATE TABLE IF NOT EXISTS alliance_players (
    discord_id INTEGER NOT NULL,
    player_id TEXT NOT NULL,
    player_name TEXT,
    PRIMARY KEY (discord_id, player_id)
);

-- Track which player has successfully redeemed which gift code
CREATE TABLE IF NOT EXISTS redemption_history (
    player_id TEXT NOT NULL,
    gift_code TEXT NOT NULL,
    redeemed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (player_id, gift_code)
);
```

### 2. Slash Commands (`GiftCog.py`)
Implement the following slash commands in a new `discord.py` Cog:
* `/register <player_id>`:
  1. Calls `/api/player` (with signature) to verify the player ID exists.
  2. If valid, retrieves their nickname/kingdom and saves the `discord_id`, `player_id`, and `player_name` into `alliance_players`.
  3. Returns a success message displaying their verified nickname.
* `/unregister <player_id>`: Removes the corresponding player ID from the player's account.
* `/redeem-force <gift_code>`: Admins can trigger an immediate bulk redemption of a specific code for all registered players in the database.

### 3. Automated Code Polling (Background Tasks)
Instead of relying on manual inputs, configure the bot container to dynamically poll for new gift codes:

1. **Active Code Source:** Use the public API endpoints of community-maintained databases (such as `kingshot.net/api/gift-codes` or similar).
2. **Background Scheduler:** Use the `tasks` extension from `discord.ext` to create a loop running in the background every 1 to 4 hours:
   ```python
   from discord.ext import tasks, commands
   import asyncio
   import random

   class GiftCog(commands.Cog):
       def __init__(self, bot):
           self.bot = bot
           self.poll_gift_codes.start()

       @tasks.loop(hours=2)
       async def poll_gift_codes(self):
           # 1. Fetch active codes from kingshot.net/api/gift-codes
           # 2. Query all unique FIDs in 'alliance_players'
           # 3. For each active code and player:
           #    - Check if (player_id, gift_code) exists in 'redemption_history'
           #    - If NOT: Execute redemption call, apply random delay, and write to 'redemption_history' upon success (or permanent failure status)
   ```

### 4. Non-Blocking Async Architecture
* **Avoid Blocking standard Discord execution:** Discord bots run in a single-threaded asynchronous loop. Do NOT use `time.sleep()` for the randomized anti-flagging delay.
* **Use Async IO:** Instead, use `await asyncio.sleep(random.uniform(2.0, 5.0))` within your redemption loop to ensure other bot functions (such as handling slash commands or posting reminders) remain perfectly responsive during bulk redemption sequences.

### 5. CAPTCHA & Machine Learning (ML) Options
When hitting API traffic thresholds, the Century Games endpoint will return a visual CAPTCHA. In a private alliance server, you have three primary ways to handle this:

* **Option A: Automated ML Solver (Fully Autonomous)**
  * **How it works:** Port the trained Convolutional Neural Network model (`captcha_model.onnx`) from the WOS repository. 
  * **Dependencies:** Add `onnxruntime`, `numpy`, and `pillow` to your bot's `requirements.txt` / Docker environment.
  * **Execution:** When the API returns a CAPTCHA challenge, download the target image, convert it to grayscale, resize it to the model's dimensions, feed it to `onnxruntime` to predict the 4 characters, and re-submit the request with `captcha_code=<solved_characters>`.
* **Option B: Manual Discord Fallback (Lightweight & Safe)**
  * **How it works:** Avoid adding heavy machine learning dependencies to your Docker container. If the bot receives a CAPTCHA response from the API, it downloads the image and posts it into a dedicated Discord channel (e.g., `#bot-captchas`), tagging the target player or administrators.
  * **Resolution:** An administrator solves the CAPTCHA by replying or using a `/captcha <code>` command. The bot caches the execution context in memory, applies the solved string to the queued request, and resumes the redemption process.
* **Option C: Warn & Skip**
  * **How it works:** If a CAPTCHA is served, skip the player, record the failure in the logs, and send a Discord message advising the player to manually redeem that specific code on the official web portal.

### 6. Edge-Cases & Optimizations to Remember
* **Cloudflare & Request Header Emulation:** The official redemption website is protected by Cloudflare. Bare HTTP client requests made from cloud hosting environments without standard headers will be flagged. Ensure your bot's HTTP request client sends complete, authentic browser headers:
  ```python
  headers = {
      "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
      "Accept": "application/json, text/plain, */*",
      "Content-Type": "application/x-www-form-urlencoded",
      "Origin": "https://kingshot-giftcode.centurygame.com",
      "Referer": "https://kingshot-giftcode.centurygame.com/"
  }
  ```
* **Guild Isolation (Multi-Server Readiness):** Even if you currently only host the bot on your own alliance server, add a `guild_id` column to the `alliance_players` table. This ensures that if you ever add the bot to allied servers or sister guilds in the future, player registries and configurations remain strictly isolated.
* **HTTP 429 Rate-Limit Graceful Backoff:** If the bot triggers an API rate limit (HTTP status `429` or dynamic server rejection), ensure your loop catches the error, halts all queued player redemptions, and pauses execution for a longer window (e.g., 60 to 120 seconds) before retrying, protecting the host's IP from firewall bans.

---

## License & Safety Notice
This tool is for educational purposes only. Automated interaction with game APIs may violate Century Games' Terms of Service. Use responsibly at your own risk.
