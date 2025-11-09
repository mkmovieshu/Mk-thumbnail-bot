# main.py (fallback simple polling using requests)
import os, time, threading, logging, json, requests
from bot import db as bot_db
import webserver

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("thumbnail-bot")

TOKEN = os.getenv("BOT_TOKEN", "").strip()
if not TOKEN:
    raise RuntimeError("BOT_TOKEN missing")
API = f"https://api.telegram.org/bot{TOKEN}"

def send_message(chat_id, text):
    try:
        requests.get(f"{API}/sendMessage", params={"chat_id": chat_id, "text": text}, timeout=10)
    except Exception:
        logger.exception("send_message failed")

def handle_update(u):
    try:
        if "message" in u:
            m = u["message"]
            chat_id = m["chat"]["id"]
            text = m.get("text","")
            if text == "/start":
                send_message(chat_id, "👋 Thumbnail Bot (fallback) is active. Use /newtemplate (not implemented).")
            # You can expand: call your db functions or simple templates handlers here.
    except Exception:
        logger.exception("handle_update error")

def polling_loop():
    offset = None
    while True:
        try:
            params = {"timeout": 30}
            if offset:
                params["offset"] = offset
            r = requests.get(API + "/getUpdates", params=params, timeout=40)
            data = r.json()
            if not data.get("ok"):
                logger.warning("getUpdates not ok: %s", data)
                time.sleep(2); continue
            for u in data.get("result", []):
                offset = u["update_id"] + 1
                handle_update(u)
        except Exception:
            logger.exception("polling crashed, retrying in 3s")
            time.sleep(3)

def run_webserver():
    try:
        webserver.run()
    except Exception:
        logger.exception("webserver crashed")

if __name__ == "__main__":
    # connect to mongo (async-run)
    try:
        import asyncio
        asyncio.run(bot_db.connect_with_retry())
    except Exception:
        logger.exception("mongo connect failed, continuing")

    # start webserver thread
    t = threading.Thread(target=run_webserver, daemon=True)
    t.start()
    logger.info("✅ Webserver started (fallback mode)")

    # start polling loop (blocking)
    polling_loop()
