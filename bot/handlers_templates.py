import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)
from bot.db import ensure_user, create_template, get_templates_for_user

logger = logging.getLogger("templates")

ASK_NAME, ASK_BUTTON_TEXT, ASK_BUTTON_URL, CONFIRM_ADD_MORE = range(4)

# -------------------------------------------------------------------
# Conversation flow
# -------------------------------------------------------------------
async def cmd_newtemplate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await ensure_user(update.effective_user)
    await update.message.reply_text("Enter template name:")
    return ASK_NAME

async def ask_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["template_name"] = update.message.text
    context.user_data["buttons"] = []
    await update.message.reply_text("Enter first button text:")
    return ASK_BUTTON_TEXT

async def ask_button_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["button_text"] = update.message.text
    await update.message.reply_text("Enter button URL:")
    return ASK_BUTTON_URL

async def ask_button_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    text = context.user_data.get("button_text")
    context.user_data["buttons"].append(
        {"text": text, "url": url}
    )

    keyboard = [
        [
            InlineKeyboardButton("➕ Add another", callback_data="add_more"),
            InlineKeyboardButton("✅ Save template", callback_data="save_template"),
        ]
    ]
    await update.message.reply_text(
        "Do you want to add another button?",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return CONFIRM_ADD_MORE

async def confirm_add_more(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "add_more":
        await query.edit_message_text("Enter next button text:")
        return ASK_BUTTON_TEXT

    elif query.data == "save_template":
        user = update.effective_user
        name = context.user_data.get("template_name")
        buttons = context.user_data.get("buttons", [])
        await create_template(user.id, name, buttons)
        await query.edit_message_text(f"✅ Template '{name}' saved successfully!")
        return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Template creation cancelled.")
    return ConversationHandler.END

# -------------------------------------------------------------------
# Commands outside conversation
# -------------------------------------------------------------------
async def cmd_mytemplates(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    templates = await get_templates_for_user(user.id)
    if not templates:
        await update.message.reply_text("You have no saved templates yet.")
        return
    text = "🧩 *Your Templates:*\n\n" + "\n".join(
        [f"• {t['name']} ({len(t['buttons'])} buttons)" for t in templates]
    )
    await update.message.reply_text(text, parse_mode="Markdown")

# -------------------------------------------------------------------
# ConversationHandler setup
# -------------------------------------------------------------------
def get_conversation_handler():
    return ConversationHandler(
        entry_points=[CommandHandler("newtemplate", cmd_newtemplate)],
        states={
            ASK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_name)],
            ASK_BUTTON_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_button_text)],
            ASK_BUTTON_URL: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_button_url)],
            CONFIRM_ADD_MORE: [CallbackQueryHandler(confirm_add_more)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True,  # per_message removed
    )
