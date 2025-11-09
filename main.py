import os
import threading
import time
import urllib.request
import logging
import asyncio
import json

from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters
from bot import handlers_templates, db as bot_db
import webserver

# Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("thumbnail-bot")

# Env
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN environment variable missing.")

# Basic command
async def start_cmd(update: Update, context):
    await update.message.reply_text("👋 Thumbnail Bot is active! Use /newtemplate to create one.")

# Helpers
def delete_webhook_if_any(token: str):
    try:
        url = f"https://api.telegram.org/bot{token}/deleteWebhook?drop_pending_updates=true"
        with urllib.request.urlopen(url, timeout=10) as r:
            resp = r.read().decode()
            logger.info("deleteWebhook response: %s", resp)
    except Exception as e:
        logger.warning("Webhook deletion failed: %s", e)

def run_webserver():
    try:
        webserver.run()
    except Exception as e:
        logger.exception("Webserver crashed: %s", e)

def ensure_mongo_connected():
    """Run the async connect_with_retry synchronously once before starting polling."""
    try:
        asyncio.run(bot_db.connect_with_retry())
    except Exception:
        logger.exception("Could not connect to MongoDB")
        raise

# Main
def main():
    logger.info("Connecting to MongoDB...")
    ensure_mongo_connected()

    delete_webhook_if_any(BOT_TOKEN)

    # start flask webserver in background thread
    t = threading.Thread(target=run_webserver, daemon=True)
    t.start()
    logger.info("✅ Webserver started in background")

    # build telegram app
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(handlers_templates.get_conversation_handler())
    app.add_handler(CommandHandler("mytemplates", handlers_templates.cmd_mytemplates))

    # optional debug handler to log incoming updates
    async def debug_all(update, context):
        logger.info("DEBUG UPDATE: %s", json.dumps(update.to_dict(), default=str))
    app.add_handler(MessageHandler(filters.ALL, debug_all), group=0)

    # Run polling inside its own asyncio.run(...) to ensure a proper loop exists.
    logger.info("🔁 Starting bot polling loop (via asyncio.run)...")
    try:
        asyncio.run(app.run_polling(drop_pending_updates=True))
    except Exception as e:
        logger.exception("Polling crashed: %s", e)
        raise

if __name__ == "__main__":
    main()
