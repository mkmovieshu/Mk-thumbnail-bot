# bot/db.py
import os
import motor.motor_asyncio
from datetime import datetime

MONGO_URI = os.getenv("MONGO_URI")
if not MONGO_URI:
    raise RuntimeError("MONGO_URI env var required.")

client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URI)
db = client.get_default_database()  # uses DB from URI if provided, else 'test'

users_coll = db["users"]
templates_coll = db["templates"]
jobs_coll = db["broadcast_jobs"]

# --- User helpers ---
async def ensure_user(telegram_user):
    """Insert or update basic user info. telegram_user is telegram.User object."""
    q = {"telegram_id": telegram_user.id}
    doc = {
        "$set": {
            "first_name": telegram_user.first_name,
            "username": getattr(telegram_user, "username", None),
            "last_seen_at": datetime.utcnow()
        },
        "$setOnInsert": {"created_at": datetime.utcnow()}
    }
    await users_coll.update_one(q, doc, upsert=True)
    return await users_coll.find_one(q)

# --- Template helpers ---
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
    res = await templates_coll.insert_one(doc)
    return await templates_coll.find_one({"_id": res.inserted_id})

async def get_templates_for_user(telegram_id):
    # return global + user-owned templates
    cursor = templates_coll.find({
        "$or": [
            {"is_global": True},
            {"owner_telegram_id": telegram_id}
        ]
    }).sort("created_at", -1)
    return await cursor.to_list(length=100)

async def get_template_by_id(tid):
    from bson import ObjectId
    return await templates_coll.find_one({"_id": ObjectId(tid)})

async def delete_template(tid, requester_id):
    from bson import ObjectId
    res = await templates_coll.delete_one({
        "_id": ObjectId(tid),
        "owner_telegram_id": requester_id
    })
    return res.deleted_count
