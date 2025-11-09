import os
import logging
import asyncio
import threading
import urllib.request
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters
from bot import handlers_templates, db as bot_db
import webserver

# ------------------------------------------------------------
# LOGGING
# ------------------------------------------------------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("thumbnail-bot")

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN not set")

# ------------------------------------------------------------
# UTILITIES
# ------------------------------------------------------------
def delete_webhook_if_any(token: str):
    try:
        url = f"https://api.telegram.org/bot{token}/deleteWebhook?drop_pending_updates=true"
        with urllib.request.urlopen(url, timeout=10) as r:
            resp = r.read().decode()
            logger.info("deleteWebhook response: %s", resp)
    except Exception as e:
        logger.warning("delete_webhook_if_any failed: %s", e)

async def start_cmd(update: Update, context):
    await update.message.reply_text("👋 Thumbnail Bot is active! Use /newtemplate to create one.")

# ------------------------------------------------------------
# RUN WEB SERVER ASYNC (non-blocking)
# ------------------------------------------------------------
async def run_webserver_async():
    loop = asyncio.get_running_loop()
    def _run():
        try:
            webserver.run()
        except Exception as e:
            logger.exception("Webserver crashed: %s", e)
    await loop.run_in_executor(None, _run)

# ------------------------------------------------------------
# MAIN BOT LOGIC
# ------------------------------------------------------------
async def main():
    await bot_db.connect_with_retry()
    delete_webhook_if_any(BOT_TOKEN)
    await asyncio.sleep(0.3)

    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(handlers_templates.get_conversation_handler())
    app.add_handler(CommandHandler("mytemplates", handlers_templates.cmd_mytemplates))

    # Debug handler
    import json
    async def debug_all(update, context):
        logging.info("DEBUG UPDATE: %s", json.dumps(update.to_dict(), default=str))
    app.add_handler(MessageHandler(filters.ALL, debug_all), group=0)

    # Run bot and webserver concurrently
    logger.info("🔁 Starting polling and webserver concurrently...")
    await asyncio.gather(
        run_webserver_async(),
        app.run_polling(close_loop=False)
    )

# ------------------------------------------------------------
# ENTRY POINT
# ------------------------------------------------------------
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped manually.")
