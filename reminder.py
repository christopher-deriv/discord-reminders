import os
import requests
import logging
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("reminder.log"),
        logging.StreamHandler()
    ]
)

# Load environment variables
load_dotenv()

WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

GIF_URL = "https://media.giphy.com/media/v1.Y2lkPTc5MGI3NjExMmdrZnhueXRqZjh6Zjh6Zjh6Zjh6Zjh6Zjh6Zjh6Zjh6Zjh6Zjh6JmVwPXYxX2ludGVybmFsX2dpZl9ieV9pZCZjdD1n/hrnYspWWhsIyA/giphy.gif"
MESSAGE = "@everyone ~ Last minute arena!"

def send_reminder():
    if not WEBHOOK_URL or WEBHOOK_URL == "your_webhook_url_here":
        logging.error("DISCORD_WEBHOOK_URL not set in .env")
        return

    payload = {
        "content": MESSAGE,
        "embeds": [
            {
                "image": {
                    "url": GIF_URL
                }
            }
        ]
    }

    try:
        response = requests.post(WEBHOOK_URL, json=payload, timeout=10)
        if response.status_code == 204:
            logging.info("Reminder sent successfully!")
        else:
            logging.error(f"Failed to send reminder. Status: {response.status_code}, Response: {response.text}")
    except Exception as e:
        logging.exception("An unexpected error occurred while sending the reminder")

if __name__ == "__main__":
    send_reminder()

