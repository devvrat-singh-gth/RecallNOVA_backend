# app/services/guard_service.py

import logging
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from pymongo import ReturnDocument

from app.config.plans import PLANS
from app.db.mongo import db
from app.services.redis_service import r


logger = logging.getLogger(__name__)

WINDOW = 60  # seconds
MAX_INPUT_CHARS = 2000

rate_limits_collection = db["rate_limits"]


RATE_LIMIT_SCRIPT = """
local current = redis.call("INCR", KEYS[1])

if current == 1 then
    redis.call("EXPIRE", KEYS[1], ARGV[1])
end

return current
"""


def get_rate_limit(plan: str) -> int:
    config = PLANS.get(plan, PLANS["free"])

    return int(
        config.get("rate_limit_per_minute", 10)
    )


def check_mongo_rate_limit(key: str, limit: int) -> bool:
    """
    Atomic MongoDB fallback for when Redis is unavailable.
    Uses a fixed 60-second window per identity and plan.
    """

    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(seconds=WINDOW)

    expired = {
        "$lte": [
            {"$ifNull": ["$expires_at", now]},
            now,
        ]
    }

    record = rate_limits_collection.find_one_and_update(
        {"_id": key},
        [
            {
                "$set": {
                    "count": {
                        "$cond": [
                            expired,
                            1,
                            {
                                "$add": [
                                    {"$ifNull": ["$count", 0]},
                                    1,
                                ]
                            },
                        ]
                    },
                    "expires_at": {
                        "$cond": [
                            expired,
                            expires_at,
                            "$expires_at",
                        ]
                    },
                }
            }
        ],
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )

    return int(record["count"]) <= limit


def check_rate_limit(
    identity_id: str,
    plan: str = "free",
) -> bool:

    limit = get_rate_limit(plan)
    key = f"rate:{plan}:{identity_id}"

    try:
        current = r.eval(
            RATE_LIMIT_SCRIPT,
            1,
            key,
            WINDOW,
        )

        return int(current) <= limit

    except Exception:
        logger.exception(
            "Redis rate limiter unavailable. Using MongoDB fallback."
        )

    try:
        return check_mongo_rate_limit(key, limit)

    except Exception as exc:
        logger.exception(
            "Both Redis and MongoDB rate limiting failed."
        )

        raise HTTPException(
            status_code=503,
            detail="Rate limiting is temporarily unavailable. Please try again.",
        ) from exc


def token_guard(text: str) -> str:
    return text[:MAX_INPUT_CHARS]