import os
import threading
import time
import urllib.request
import logging

from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters
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
    raise RuntimeError("BOT_TOKEN environment variable missing.")

# -------------------------------------------------------------------
# BASIC COMMANDS
# -------------------------------------------------------------------
async def start_cmd(update: Update, context):
    await update.message.reply_text(
        "👋 Thumbnail Bot is active!\nUse /newtemplate to create a new one."
    )

# -------------------------------------------------------------------
# UTILITIES
# -------------------------------------------------------------------
def delete_webhook_if_any(token: str):
    """Ensure webhook is cleared before polling starts."""
    try:
        url = f"https://api.telegram.org/bot{token}/deleteWebhook?drop_pending_updates=true"
        with urllib.request.urlopen(url, timeout=10) as r:
            resp = r.read().decode()
            logger.info("deleteWebhook response: %s", resp)
    except Exception as e:
        logger.warning("Webhook deletion failed: %s", e)

def run_webserver():
    """Run Flask webserver in background (for Render keep-alive pings)."""
    try:
        webserver.run()
    except Exception as e:
        logger.error("Webserver crashed: %s", e)

# -------------------------------------------------------------------
# MAIN RUNNER
# -------------------------------------------------------------------
def main():
    logger.info("Connecting to MongoDB...")
    import asyncio
    asyncio.run(bot_db.connect_with_retry())

    delete_webhook_if_any(BOT_TOKEN)

    # Start Flask server on a background thread
    t = threading.Thread(target=run_webserver, daemon=True)
    t.start()
    logger.info("✅ Webserver started in background")

    # Build Telegram application
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(handlers_templates.get_conversation_handler())
    app.add_handler(CommandHandler("mytemplates", handlers_templates.cmd_mytemplates))

    # Debug handler (optional)
    import json
    async def debug_all(update, context):
        logging.info("DEBUG UPDATE: %s", json.dumps(update.to_dict(), default=str))
    app.add_handler(MessageHandler(filters.ALL, debug_all), group=0)

    # Run bot polling (blocking)
    logger.info("🔁 Starting bot polling loop...")
    app.run_polling(drop_pending_updates=True)

# -------------------------------------------------------------------
# ENTRY POINT
# -------------------------------------------------------------------
if __name__ == "__main__":
    main()
