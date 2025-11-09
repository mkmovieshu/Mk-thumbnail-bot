# main.py
import os
import threading
import time
import urllib.request
import logging
import asyncio

from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler

# local modules
import webserver
from bot import handlers_templates
from bot import db as bot_db

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("thumbnail-bot")

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
if not BOT_TOKEN:
    logger.error("BOT_TOKEN not set")
    raise RuntimeError("BOT_TOKEN required")

def delete_webhook_if_any(token: str):
    try:
        url = f"https://api.telegram.org/bot{token}/deleteWebhook?drop_pending_updates=true"
        with urllib.request.urlopen(url, timeout=10) as r:
            resp = r.read().decode()
            logger.info("deleteWebhook response: %s", resp)
    except Exception as e:
        logger.warning("delete_webhook_if_any failed (non-fatal): %s", e)

async def start_cmd(update: Update, context):
    await update.message.reply_text("👋 Thumbnail Bot is active! Use /newtemplate")

async def main_async():
    # Connect DB (with retries inside bot_db.connect_with_retry)
    await bot_db.connect_with_retry()

    # Remove webhook to prevent getUpdates conflict
    delete_webhook_if_any(BOT_TOKEN)
    await asyncio.sleep(0.3)

    # Build and start telegram app
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(handlers_templates.get_conversation_handler())
    app.add_handler(CommandHandler("mytemplates", handlers_templates.cmd_mytemplates))

    logger.info("🔁 Initializing Telegram application...")
    await app.initialize()
    await app.start()

    logger.info("🔁 Starting updater/polling...")
    await app.updater.start_polling()
    # keep the app running until stopped
    await app.updater.idle()

def start_webserver_thread():
    # run Flask in a separate thread (blocking)
    def _run():
        try:
            webserver.run()
        except Exception as e:
            logger.exception("Webserver thread crashed: %s", e)
    t = threading.Thread(target=_run, daemon=True)
    t.start()
    logger.info("Webserver started on thread")

def run():
    start_webserver_thread()
    # Control whether to run polling (use RUN_POLLING env if you ever want web-only)
    if os.getenv("RUN_POLLING", "1") != "1":
        logger.info("RUN_POLLING != 1 -> running webserver only. Main process sleeping.")
        while True:
            time.sleep(30)

    try:
        asyncio.run(main_async())
    except Exception:
        logger.exception("Fatal exception in main_async")
        raise

if __name__ == "__main__":
    run()
