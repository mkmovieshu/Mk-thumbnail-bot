from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Hello! Thumbnail Bot is active!")

app = ApplicationBuilder().token("YOUR_BOT_TOKEN_HERE").build()
app.add_handler(CommandHandler("start", start))

app.run_polling()
