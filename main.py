# main.py
import os
import threading
import time
import urllib.request
import logging
import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler

from bot import handlers_templates
from bot import db as bot_db

import webserver  # Flask health server (separate thread)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("thumbnail-bot")

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN not set")

def delete_webhook_if_any(token: str):
    """Remove webhook to avoid polling conflicts."""
    try:
        url = f"https://api.telegram.org/bot{token}/deleteWebhook?drop_pending_updates=true"
        with urllib.request.urlopen(url, timeout=10) as r:
            resp = r.read().decode()
            logger.info("deleteWebhook response: %s", resp)
    except Exception as e:
        logger.warning("delete_webhook_if_any failed: %s", e)

async def start_cmd(update: Update, context):
    await update.message.reply_text("👋 Thumbnail Bot is active! Use /newtemplate to create templates.")

async def main_async():
    await bot_db.connect_with_retry()
    delete_webhook_if_any(BOT_TOKEN)

    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(handlers_templates.get_conversation_handler())
    app.add_handler(CommandHandler("mytemplates", handlers_templates.cmd_mytemplates))

    logger.info("🔁 Starting bot polling...")
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    await app.updater.idle()

def start_webserver():
    """Run Flask webserver on a completely separate thread & loop."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    webserver.run()  # Flask's blocking server runs here

def run():
    # start webserver in separate event loop thread
    threading.Thread(target=start_webserver, daemon=True).start()
    logger.info("Webserver started on thread")

    if os.getenv("RUN_POLLING", "1") == "1":
        asyncio.run(main_async())
    else:
        logger.info("RUN_POLLING=0 set — webserver only mode.")
        while True:
            time.sleep(30)

if __name__ == "__main__":
    run()
