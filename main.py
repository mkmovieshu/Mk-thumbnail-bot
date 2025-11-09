import os
import threading
import time
import urllib.request
import logging
import asyncio

from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler
from bot import handlers_templates, db as bot_db
import webserver

# -------------------------------------------------------------------
# LOGGING CONFIG
# -------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger("thumbnail-bot")

# -------------------------------------------------------------------
# ENVIRONMENT VARIABLES
# -------------------------------------------------------------------
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
if not BOT_TOKEN:
    logger.error("BOT_TOKEN is not set.")
    raise RuntimeError("BOT_TOKEN required.")

# -------------------------------------------------------------------
# BASIC COMMANDS
# -------------------------------------------------------------------
async def start_cmd(update: Update, context):
    await update.message.reply_text("👋 Thumbnail Bot is active! Use /newtemplate to create one.")

# -------------------------------------------------------------------
# UTILITIES
# -------------------------------------------------------------------
def delete_webhook_if_any(token: str):
    """Ensure no webhook is set (avoid getUpdates conflict)."""
    try:
        url = f"https://api.telegram.org/bot{token}/deleteWebhook?drop_pending_updates=true"
        with urllib.request.urlopen(url, timeout=10) as r:
            resp = r.read().decode()
            logger.info("deleteWebhook response: %s", resp)
    except Exception as e:
        logger.warning("delete_webhook_if_any failed (non-fatal): %s", e)

def start_webserver_thread():
    """Run Flask webserver in background thread (for Render keepalive)."""
    def _run():
        try:
            webserver.run()
        except Exception as e:
            logger.exception("Webserver crashed: %s", e)
    t = threading.Thread(target=_run, daemon=True)
    t.start()
    logger.info("✅ Webserver started on thread")

# -------------------------------------------------------------------
# MAIN ASYNC LOOP
# -------------------------------------------------------------------
async def main_async():
    # Connect MongoDB (retry logic handled inside db.py)
    await bot_db.connect_with_retry()

    # Remove webhook to allow polling
    delete_webhook_if_any(BOT_TOKEN)
    await asyncio.sleep(0.3)

    # Build Telegram app
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(handlers_templates.get_conversation_handler())
    app.add_handler(CommandHandler("mytemplates", handlers_templates.cmd_mytemplates))

    # Debug handler (helps verify incoming updates)
    from telegram.ext import MessageHandler, filters
    import json
    async def debug_all(update, context):
        logging.info("DEBUG UPDATE: %s", json.dumps(update.to_dict(), default=str))
    app.add_handler(MessageHandler(filters.ALL, debug_all), group=0)

    # Start polling
    logger.info("🔁 Starting bot polling loop...")
    try:
        await app.initialize()
        await app.start()
        await app.updater.start_polling()
        await app.updater.idle()  # Keeps running forever
    except Exception as e:
        logger.exception("Polling crashed: %s", e)
        raise

# -------------------------------------------------------------------
# RUNNER
# -------------------------------------------------------------------
def run():
    """Start webserver + telegram bot in same Render Web Service."""
    start_webserver_thread()

    # Keep only one event loop running forever
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(main_async())
    except KeyboardInterrupt:
        logger.info("Bot stopped manually.")
    except Exception:
        logger.exception("Bot crashed.")
    finally:
        loop.close()

# -------------------------------------------------------------------
# ENTRY POINT
# -------------------------------------------------------------------
if __name__ == "__main__":
    run()
