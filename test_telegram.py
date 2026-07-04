import os
import httpx
from dotenv import load_dotenv

# Load env variables
load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

if not BOT_TOKEN:
    print("[Error] TELEGRAM_BOT_TOKEN is not configured in your .env file!")
    exit(1)

if not CHAT_ID:
    print("[Error] TELEGRAM_CHAT_ID is not configured in your .env file!")
    print("-> To find your Chat ID:")
    print("   1. Open Telegram and search for '@userinfobot'.")
    print("   2. Start the bot / send any message to it.")
    print("   3. It will reply with your 'Id'. Copy and paste this ID into your .env file.")
    print("\n[Warning] Also remember to search for your own bot on Telegram and click 'Start' so it can message you!")
    exit(1)

print(f"Connecting to Telegram Bot API with token: {BOT_TOKEN[:10]}...{BOT_TOKEN[-5:]}")
print(f"Sending test message to Chat ID: {CHAT_ID}")

url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
payload = {
    "chat_id": CHAT_ID,
    "text": "CineWatch Telegram Bot integration successfully verified! You will receive show time notifications here.",
    "parse_mode": "Markdown"
}

try:
    response = httpx.post(url, json=payload, timeout=10)
    if response.status_code == 200:
        print("[Success] Test message sent to your Telegram bot.")
    else:
        print(f"[Error] Telegram API Error (Status {response.status_code}): {response.text}")
except Exception as e:
    print(f"[Error] Network or connection error: {e}")
