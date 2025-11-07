from bot.handlers_templates import get_conversation_handler, cmd_mytemplates

def run_bot():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(get_conversation_handler())
    app.add_handler(CommandHandler("mytemplates", cmd_mytemplates))

    print("🔁 Starting bot polling...")
    app.run_polling()
