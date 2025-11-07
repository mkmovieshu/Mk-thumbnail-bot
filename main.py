# main.py (or bot/main.py depending on your layout)
from telegram.ext import ApplicationBuilder, CommandHandler
import os
import threading
import webserver

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN env var required.")

def run_bot():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # import handlers lazily to avoid import cycles
    from bot.handlers_templates import cmd_newtemplate, cmd_mytemplates

    app.add_handler(CommandHandler("start", lambda u,c: u.message.reply_text("Bot active")))
    app.add_handler(CommandHandler("newtemplate", cmd_newtemplate))
    app.add_handler(CommandHandler("mytemplates", cmd_mytemplates))

    print("🔁 Starting bot polling...")
    app.run_polling()

if __name__ == "__main__":
    threading.Thread(target=webserver.run, daemon=True).start()
    run_bot()
