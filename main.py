# main.py
import os
import threading
import time
import urllib.request
import logging

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
)

# local webserver (must exist as webserver.py in repo root)
import webserver

# handlers that depend on DB (ensure these files exist in bot/)
# get_conversation_handler() provides /newtemplate ConversationHandler
# cmd_mytemplates handles /mytemplates
from bot.handlers_templates import get_conversation_handler, cmd_mytemplates

# --- config / logging ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    logger.error("BOT_TOKEN env var missing. Set it in Render environment.")
    raise RuntimeError("BOT_TOKEN env var required.")

def delete_webhook_if_any(token: str):
    """Try removing webhook to avoid getUpdates conflict (safe to call)."""
    try:
        url = f"https://api.telegram.org/bot{token}/deleteWebhook?drop_pending_updates=true"
        with urllib.request.urlopen(url, timeout=10) as r:
            resp = r.read().decode()
            logger.info("deleteWebhook response: %s", resp)
    except Exception as e:
        logger.warning("delete_webhook_if_any failed: %s", e)

async def start_cmd(update: Update, context):
    await update.message.reply_text("👋 Thumbnail Bot is active! Use /newtemplate to create templates.")

def run_bot():
    """Build app, register handlers, remove webhook, then start polling."""
    # Build app
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Register basic handlers
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(get_conversation_handler())
    app.add_handler(CommandHandler("mytemplates", cmd_mytemplates))

    # Remove webhook first to avoid conflict with getUpdates/polling
    logger.info("Removing webhook (if any) before starting polling...")
    delete_webhook_if_any(BOT_TOKEN)
    # small sleep to let Telegram process deletion (optional, safe)
    time.sleep(0.5)

    logger.info("🔁 Starting bot polling...")
    app.run_polling()

if __name__ == "__main__":
    # always run lightweight webserver (health endpoint)
    server_thread = threading.Thread(target=webserver.run, daemon=True)
    server_thread.start()
    logger.info("Webserver thread started (health endpoint).")

    # control polling via environment variable (default = "1")
    run_polling = os.getenv("RUN_POLLING", "1")
    if run_polling == "1":
        try:
            run_bot()
        except Exception as e:
            logger.exception("Bot exited with exception: %s", e)
            raise
    else:
        logger.info("RUN_POLLING != 1 — running webserver only. PID: %s", os.getpid())
        server_thread.join()
