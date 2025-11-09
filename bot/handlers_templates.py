from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    filters,
)
from bot.db import ensure_user, create_template, get_templates_for_user

# --- Conversation states ---
ASK_NAME, ASK_BUTTON_TEXT, ASK_BUTTON_URL, CONFIRM_ADD_MORE = range(4)


# ---------- /newtemplate ----------
async def cmd_newtemplate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await ensure_user(update.effective_user)
    await update.message.reply_text("🎨 Please enter a name for your new template:")
    context.user_data["buttons"] = []
    return ASK_NAME


async def ask_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.text.strip()
    if not name:
        await update.message.reply_text("❌ Please provide a valid template name.")
        return ASK_NAME
    context.user_data["template_name"] = name
    await update.message.reply_text("🔘 Now enter the first button text:")
    return ASK_BUTTON_TEXT


async def ask_button_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["current_button_text"] = update.message.text.strip()
    await update.message.reply_text("🔗 Enter the URL for this button:")
    return ASK_BUTTON_URL


async def ask_button_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = context.user_data.get("current_button_text")
    url = update.message.text.strip()
    if not url.startswith("http"):
        await update.message.reply_text("❌ Invalid URL. Must start with http.")
        return ASK_BUTTON_URL

    buttons = context.user_data.get("buttons", [])
    buttons.append([InlineKeyboardButton(text, url=url)])
    context.user_data["buttons"] = buttons

    keyboard = [
        [InlineKeyboardButton("➕ Add More Buttons", callback_data="add_more")],
        [InlineKeyboardButton("✅ Save Template", callback_data="save_template")],
        [InlineKeyboardButton("❌ Cancel", callback_data="cancel")],
    ]
    await update.message.reply_text(
        f"Button '{text}' added.\nWhat would you like to do next?",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return CONFIRM_ADD_MORE


async def confirm_add_more(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "add_more":
        await query.edit_message_text("🔘 Enter next button text:")
        return ASK_BUTTON_TEXT

    elif query.data == "save_template":
        user = update.effective_user
        name = context.user_data.get("template_name", "Untitled")
        buttons = context.user_data.get("buttons", [])
        if not buttons:
            await query.edit_message_text("❌ No buttons found in this template.")
            return ConversationHandler.END

        await create_template(user.id, name, buttons)
        await query.edit_message_text(f"✅ Template '{name}' saved successfully.")
        return ConversationHandler.END

    else:  # cancel
        await query.edit_message_text("🚫 Cancelled.")
        return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Cancelled.")
    return ConversationHandler.END


def get_conversation_handler():
    """Return the conversation handler for /newtemplate flow."""
    return ConversationHandler(
        entry_points=[CommandHandler("newtemplate", cmd_newtemplate)],
        states={
            ASK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_name)],
            ASK_BUTTON_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_button_text)],
            ASK_BUTTON_URL: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_button_url)],
            CONFIRM_ADD_MORE: [CallbackQueryHandler(confirm_add_more)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True,
        per_message=True,
    )


# ---------- /mytemplates ----------
async def cmd_mytemplates(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await ensure_user(user)
    templates = await get_templates_for_user(user.id)

    if not templates:
        await update.message.reply_text("😕 You don't have any saved templates yet.")
        return

    lines = ["📋 Your templates:\n"]
    for t in templates:
        name = t.get("name", "Unnamed")
        count = len(t.get("buttons", []))
        lines.append(f"• {name} ({count} buttons)")

    await update.message.reply_text("\n".join(lines))
