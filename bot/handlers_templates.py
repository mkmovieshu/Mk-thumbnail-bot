# bot/handlers_templates.py
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    ContextTypes,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    CallbackQueryHandler,
    filters,
)
from bot.db import ensure_user, create_template, get_templates_for_user
import asyncio

# States
ASK_NAME, ASK_BUTTON_TEXT, ASK_BUTTON_URL, CONFIRM_ADD_MORE = range(4)

# Temporary user session store
user_sessions = {}

async def cmd_newtemplate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await ensure_user(user)
    await update.message.reply_text("📝 Template name ఇవ్వండి:")
    return ASK_NAME

async def ask_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.text.strip()
    context.user_data["template_name"] = name
    context.user_data["buttons"] = []
    await update.message.reply_text("🔘 మొదటి బటన్ text ఇవ్వండి:")
    return ASK_BUTTON_TEXT

async def ask_button_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    btn_text = update.message.text.strip()
    context.user_data["current_btn_text"] = btn_text
    await update.message.reply_text("🔗 ఆ బటన్ URL ఇవ్వండి:")
    return ASK_BUTTON_URL

async def ask_button_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    btn_text = context.user_data["current_btn_text"]
    buttons = context.user_data.get("buttons", [])
    buttons.append({"type": "url", "text": btn_text, "url": url})
    context.user_data["buttons"] = buttons

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ మరో బటన్", callback_data="add_more"),
         InlineKeyboardButton("✅ Save", callback_data="save_template")]
    ])
    await update.message.reply_text("బటన్ జత చేయబడింది!", reply_markup=keyboard)
    return CONFIRM_ADD_MORE

async def confirm_add_more(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "add_more":
        await query.edit_message_text("🔘 కొత్త బటన్ text ఇవ్వండి:")
        return ASK_BUTTON_TEXT
    elif query.data == "save_template":
        user = update.effective_user
        name = context.user_data.get("template_name")
        buttons = context.user_data.get("buttons", [])
        tpl = await create_template(user.id, name, buttons)
        await query.edit_message_text(f"✅ Template saved!\nName: {name}\nButtons: {len(buttons)}")
        return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Template creation canceled.")
    return ConversationHandler.END


def get_conversation_handler():
    return ConversationHandler(
    entry_points=[CommandHandler("newtemplate", cmd_newtemplate)],
    states={ ... },
    fallbacks=[CommandHandler("cancel", cancel)],
    allow_reentry=True,
    per_message=True 
    )

async def cmd_mytemplates(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    templates = await get_templates_for_user(user.id)
    if not templates:
        await update.message.reply_text("⚠️ మీరు ఎలాంటి templates సృష్టించలేదు.")
        return

    lines = [f"🧩 **{t['name']}** — {len(t['buttons'])} బటన్లు" for t in templates]
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
