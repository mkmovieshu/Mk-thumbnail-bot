# bot/db.py
import os
import asyncio
import logging
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime

logger = logging.getLogger(__name__)

MONGO_URI = os.getenv("MONGO_URI", "").strip()
_DB_NAME = os.getenv("MONGO_DBNAME", "thumbnail_bot")  # optional override

_client = None
db = None

async def connect_with_retry(retries=5, delay=2):
    global _client, db
    if not MONGO_URI:
        raise RuntimeError("MONGO_URI not set in environment")

    for attempt in range(1, retries + 1):
        try:
            _client = AsyncIOMotorClient(MONGO_URI, serverSelectionTimeoutMS=5000)
            # try a lightweight call to ensure connection
            await _client.admin.command("ping")
            db = _client.get_database(_DB_NAME)
            logger.info("Connected to MongoDB (db=%s)", _DB_NAME)
            return
        except Exception as exc:
            logger.warning("Mongo connect attempt %d failed: %s", attempt, exc)
            if attempt == retries:
                logger.error("MongoDB connect failed after %d attempts", retries)
                raise
            await asyncio.sleep(delay * attempt)

# helpers that assume connect_with_retry() was called at startup
users_coll = lambda: db["users"]
templates_coll = lambda: db["templates"]

async def ensure_user(telegram_user):
    q = {"telegram_id": telegram_user.id}
    doc = {
        "$set": {
            "first_name": telegram_user.first_name,
            "username": getattr(telegram_user, "username", None),
            "last_seen_at": datetime.utcnow()
        },
        "$setOnInsert": {"created_at": datetime.utcnow()}
    }
    await users_coll().update_one(q, doc, upsert=True)
    return await users_coll().find_one(q)

async def create_template(owner_telegram_id, name, buttons, is_global=False):
    now = datetime.utcnow()
    doc = {
        "owner_telegram_id": owner_telegram_id,
        "name": name,
        "buttons": buttons,
        "is_global": bool(is_global),
        "created_at": now,
        "updated_at": now
    }
    res = await templates_coll().insert_one(doc)
    return await templates_coll().find_one({"_id": res.inserted_id})

async def get_templates_for_user(telegram_id, limit=100):
    cursor = templates_coll().find({
        "$or": [
            {"is_global": True},
            {"owner_telegram_id": telegram_id}
        ]
    }).sort("created_at", -1)
    return await cursor.to_list(length=limit)
