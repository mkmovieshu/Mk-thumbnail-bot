# bot/handlers_templates.py
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler
from bot.db import ensure_user, create_template, get_templates_for_user
import json

async def cmd_newtemplate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await ensure_user(user)
    # expect payload as JSON after command, e.g.: /newtemplate {"name":"A","buttons":[{"type":"url","text":"Play","url":"https://..."}]}
    raw = " ".join(context.args)  # command args
    if not raw:
        await update.message.reply_text("Use: /newtemplate {json}\nExample:\n/newtemplate {\"name\":\"My\",\"buttons\":[{\"type\":\"url\",\"text\":\"YT\",\"url\":\"https://youtube.com\"}]}")
        return
    try:
        data = json.loads(raw)
        name = data.get("name", "Unnamed")
        buttons = data.get("buttons", [])
    except Exception as e:
        await update.message.reply_text("Invalid JSON. Error: " + str(e))
        return

    tpl = await create_template(user.id, name, buttons, is_global=False)
    await update.message.reply_text(f"Template saved: {tpl['_id']}")

async def cmd_mytemplates(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await ensure_user(user)
    templates = await get_templates_for_user(user.id)
    if not templates:
        await update.message.reply_text("No templates found.")
        return
    texts = []
    for t in templates:
        tid = str(t["_id"])
        name = t.get("name", "<no-name>")
        texts.append(f"{name} — id: `{tid}`")
    await update.message.reply_text("\n".join(texts), parse_mode="Markdown")
