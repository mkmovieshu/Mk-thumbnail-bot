# main.py
import os
import threading
import urllib.request
import json
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

import webserver  # existing webserver.py that binds PORT for Render

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN env var required.")

def delete_webhook_if_any(token: str):
    try:
        url = f"https://api.telegram.org/bot{token}/deleteWebhook?drop_pending_updates=true"
        with urllib.request.urlopen(url, timeout=10) as r:
            resp = r.read().decode()
            # optional: check resp for ok:true
            # print("deleteWebhook:", resp)
    except Exception as e:
        # swallow network errors but log to stdout for Render logs
        print("delete_webhook_if_any error:", e)

async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Thumbnail Bot is active!")

def run_bot():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_cmd))

    # Before starting polling, try to remove webhook so getUpdates (polling) won't conflict.
    delete_webhook_if_any(BOT_TOKEN)

    print("🔁 Starting bot polling...")
    app.run_polling()

if __name__ == "__main__":
    # always run webserver for health endpoint
    server_thread = threading.Thread(target=webserver.run, daemon=True)
    server_thread.start()

    # control whether to run polling by env var (default = 1)
    if os.getenv("RUN_POLLING", "1") == "1":
        run_bot()
    else:
        print("RUN_POLLING=0 set — webserver only (no polling).")
        server_thread.join()
