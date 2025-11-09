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
    try:
        webserver.run()
    except Exception as e:
        logger.exception("Webserver crashed: %s", e)

def main():
    # 1) create and set event loop for main thread
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    # 2) connect to MongoDB (async) before starting bot
    logger.info("Connecting to MongoDB...")
    try:
        loop.run_until_complete(bot_db.connect_with_retry())
        logger.info("Connected to MongoDB (db=thumbnail_bot)")
    except Exception:
        logger.exception("Failed to connect to MongoDB")
        raise

    # 3) ensure webhook cleared
    delete_webhook_if_any(BOT_TOKEN)

    # 4) start Flask webserver in background thread (keeps Render happy)
    t = threading.Thread(target=run_webserver, daemon=True)
    t.start()
    logger.info("✅ Webserver started in background")

    # 5) build application and register handlers
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(handlers_templates.get_conversation_handler())
    app.add_handler(CommandHandler("mytemplates", handlers_templates.cmd_mytemplates))

    # optional debug handler
    async def debug_all(update, context):
        logger.info("DEBUG UPDATE: %s", json.dumps(update.to_dict(), default=str))
    app.add_handler(MessageHandler(filters.ALL, debug_all), group=0)

    # 6) initialize and start app, then start polling (all using same loop)
    try:
        logger.info("🔁 Initializing and starting Telegram application...")
        loop.run_until_complete(app.initialize())
        loop.run_until_complete(app.start())

        logger.info("🔁 Starting updater/polling...")
        loop.run_until_complete(app.updater.start_polling())

        # 7) keep process alive and let asyncio handle polling callbacks
        logger.info("✅ Bot is now polling — entering loop.run_forever()")
        loop.run_forever()

    except Exception:
        logger.exception("Polling crashed.")
        # try graceful shutdown if possible
        try:
            loop.run_until_complete(app.shutdown())
        except Exception:
            logger.exception("Error during shutdown")
        finally:
            loop.stop()
            raise

if __name__ == "__main__":
    main()
