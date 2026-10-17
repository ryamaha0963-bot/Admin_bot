import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()]
DB_PATH = os.getenv("DB_PATH", "bot.db")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable is missing!")
