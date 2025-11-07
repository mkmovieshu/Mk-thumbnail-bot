from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import os
import threading
from bot import webserver  # local webserver to keep process alive on some hosts

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN env var required. Set it in your host / secrets.")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Hello! Thumbnail Bot is active.\nUse /help to see commands.")

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("/start - check bot\n/help - this help\n/mytemplates - list templates (demo)")

async def mytemplates(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # placeholder demo: in real app load user templates from DB or files
    await update.message.reply_text("📂 You have no templates yet. Use /newtemplate to create one (not implemented in demo).")

def run_bot():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("mytemplates", mytemplates))
    print("🔁 Starting bot polling...")
    app.run_polling()

if __name__ == "__main__":
    # start lightweight webserver (some hosts require a web port)
    server_thread = threading.Thread(target=webserver.run, daemon=True)
    server_thread.start()

    run_bot()
