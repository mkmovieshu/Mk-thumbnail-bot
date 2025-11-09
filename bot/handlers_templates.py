import asyncio
import logging
import threading
import os

from flask import Flask
from bot import db as bot_db
from bot.handlers_templates import setup_template_handlers
from telegram.ext import ApplicationBuilder, CommandHandler

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("main")

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN not found in environment variables")

app_flask = Flask(__name__)

@app_flask.route("/")
def home():
    return "✅ Thumbnail Bot is Live!"

async def run_bot():
    """Runs Telegram bot polling loop."""
    logger.info("Connecting to MongoDB...")
    await bot_db.connect_with_retry()
    logger.info("Connected to MongoDB (db=thumbnail_bot)")

    bot_app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Register command handlers
    setup_template_handlers(bot_app)

    # Delete webhook just in case
    await bot_app.bot.delete_webhook(drop_pending_updates=True)

    logger.info("🤖 Starting bot polling...")
    await bot_app.run_polling(drop_pending_updates=True)

def start_flask():
    """Starts Flask web server."""
    app_flask.run(host="0.0.0.0", port=10000)

def main():
    # Start Flask webserver in background thread
    t = threading.Thread(target=start_flask, daemon=True)
    t.start()
    logger.info("✅ Webserver started in background")

    # Start bot (async)
    asyncio.run(run_bot())

if __name__ == "__main__":
    main()
