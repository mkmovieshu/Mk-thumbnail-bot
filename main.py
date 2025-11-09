# main.py
import os
import threading
import urllib.request
import logging
import asyncio
import json
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters
from bot import handlers_templates, db as bot_db
import webserver

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("thumbnail-bot")

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN environment variable missing.")

# simple start command handler
async def start_cmd(update: Update, context):
    await update.message.reply_text("👋 Thumbnail Bot is active! Use /newtemplate to create one.")

def delete_webhook_if_any(token: str):
    try:
        url = f"https://api.telegram.org/bot{token}/deleteWebhook?drop_pending_updates=true"
        with urllib.request.urlopen(url, timeout=10) as r:
            resp = r.read().decode()
            logger.info("deleteWebhook response: %s", resp)
    except Exception as e:
        logger.warning("Webhook deletion failed: %s", e)

def run_webserver():
    """Run Flask webserver (blocking) in main thread for Render health checks."""
    try:
        webserver.run()
    except Exception as e:
        logger.exception("Webserver crashed: %s", e)

def polling_worker():
    """
    Runs in its own thread. Creates a fresh asyncio event loop via asyncio.run()
    so python-telegram-bot's async lifecycle is isolated from the main thread.
    """
    async def _worker():
        # connect to mongo (inside this event loop)
        await bot_db.connect_with_retry()

        # ensure webhook cleared
        delete_webhook_if_any(BOT_TOKEN)
        await asyncio.sleep(0.1)

        # build PTB application and handlers
        app = ApplicationBuilder().token(BOT_TOKEN).build()
        app.add_handler(CommandHandler("start", start_cmd))
        app.add_handler(handlers_templates.get_conversation_handler())
        app.add_handler(CommandHandler("mytemplates", handlers_templates.cmd_mytemplates))

        # optional debug handler (remove in production)
        async def debug_all(update, context):
            logger.info("DEBUG UPDATE: %s", json.dumps(update.to_dict(), default=str))
        app.add_handler(MessageHandler(filters.ALL, debug_all), group=0)

        logger.info("🔁 Polling worker: starting app.run_polling()")
        # this will block inside asyncio.run until stopped
        await app.run_polling()

    try:
        asyncio.run(_worker())
    except Exception:
        logger.exception("Polling worker crashed")

def main():
    # 1) Start polling thread (daemon)
    t = threading.Thread(target=polling_worker, daemon=True)
    t.start()
    logger.info("✅ Polling thread started")

    # 2) Run Flask webserver in main thread (blocking)
    run_webserver()  # this keeps the process alive and exposes port for Render

if __name__ == "__main__":
    main()
