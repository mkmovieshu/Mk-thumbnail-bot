# main.py
import os
import threading
import time
import urllib.request
import logging
import asyncio

from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler

# local webserver
import webserver

# db and handlers are inside bot/ ; handlers expect db to be ready
from bot import handlers_templates  # module (register functions)
from bot import db as bot_db

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
if not BOT_TOKEN:
    logger.error("BOT_TOKEN missing. Set Render env BOT_TOKEN.")
    raise RuntimeError("BOT_TOKEN missing")

def delete_webhook_if_any(token: str):
    try:
        url = f"https://api.telegram.org/bot{token}/deleteWebhook?drop_pending_updates=true"
        with urllib.request.urlopen(url, timeout=10) as r:
            resp = r.read().decode()
            logger.info("deleteWebhook response: %s", resp)
    except Exception as e:
        logger.warning("delete_webhook_if_any failed (non-fatal): %s", e)

async def start_async():
    # 1) connect to MongoDB with retries
    await bot_db.connect_with_retry(retries=5, delay=2)

    # 2) build application and register handlers AFTER DB connected
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_cmd))
    # register conversation handler factory from handlers_templates
    app.add_handler(handlers_templates.get_conversation_handler())
    app.add_handler(CommandHandler("mytemplates", handlers_templates.cmd_mytemplates))

    # ensure webhook is deleted (avoid conflict)
    delete_webhook_if_any(BOT_TOKEN)
    # slight pause
    await asyncio.sleep(0.5)

    logger.info("🔁 Starting polling...")
    await app.run_polling()

async def start_cmd(update: Update, context):
    await update.message.reply_text("👋 Thumbnail Bot is active! Use /newtemplate")

def run():
    # start webserver thread for health
    server_thread = threading.Thread(target=webserver.run, daemon=True)
    server_thread.start()
    logger.info("Webserver started on thread")

    # control polling via env
    if os.getenv("RUN_POLLING", "1") != "1":
        logger.info("RUN_POLLING !=1 — not running polling. Exiting main loop.")
        server_thread.join()
        return

    # run main async startup
    try:
        asyncio.run(start_async())
    except Exception as e:
        logger.exception("Fatal in start_async: %s", e)
        raise

if __name__ == "__main__":
    run()
