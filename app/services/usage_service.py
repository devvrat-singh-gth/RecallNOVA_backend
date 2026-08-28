# app/services/usage_service.py

from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pymongo import ReturnDocument

from app.db.mongo import (
    monthly_usage,
    usage_tracking,
)


USAGE_COUNTERS = (
    "messages",
    "flashcard_generations",
    "quiz_generations",
)


def get_valid_timezone(
    timezone_name: str | None,
) -> ZoneInfo:

    if not timezone_name:
        return ZoneInfo("UTC")

    try:
        return ZoneInfo(
            timezone_name
        )

    except ZoneInfoNotFoundError:
        return ZoneInfo("UTC")


def get_periods(
    timezone_name: str | None,
):
    tz = get_valid_timezone(
        timezone_name
    )

    local_now = (
        datetime.now(
            timezone.utc
        ).astimezone(tz)
    )

    return (
        local_now.strftime("%Y-%m-%d"),
        local_now.strftime("%Y-%m"),
    )


def _empty_usage():
    return {
        "messages": 0,
        "flashcard_generations": 0,
        "quiz_generations": 0,
    }


def get_daily_usage(
    user_id: str,
    timezone_name: str | None,
):
    daily_period, _ = get_periods(
        timezone_name
    )

    document = usage_tracking.find_one(
        {
            "user_id": user_id,
            "daily_period": daily_period,
        }
    )

    if document:
        return {
            "messages": int(
                document.get(
                    "messages",
                    0,
                )
            ),
            "flashcard_generations": int(
                document.get(
                    "flashcard_generations",
                    0,
                )
            ),
            "quiz_generations": int(
                document.get(
                    "quiz_generations",
                    0,
                )
            ),
        }

    return _empty_usage()


def get_monthly_usage(
    user_id: str,
    timezone_name: str | None,
):
    _, monthly_period = get_periods(
        timezone_name
    )

    document = monthly_usage.find_one(
        {
            "user_id": user_id,
            "monthly_period": monthly_period,
        }
    )

    if document:
        return {
            "messages": int(
                document.get(
                    "messages",
                    0,
                )
            ),
            "flashcard_generations": int(
                document.get(
                    "flashcard_generations",
                    0,
                )
            ),
            "quiz_generations": int(
                document.get(
                    "quiz_generations",
                    0,
                )
            ),
        }

    return _empty_usage()


def get_usage(
    user_id: str,
    timezone_name: str | None,
):
    daily = get_daily_usage(
        user_id,
        timezone_name,
    )

    monthly = get_monthly_usage(
        user_id,
        timezone_name,
    )

    # Keep top-level counters for
    # backward compatibility.
    return {
        "messages": daily["messages"],
        "flashcard_generations":
            daily["flashcard_generations"],
        "quiz_generations":
            daily["quiz_generations"],

        "daily": daily,
        "monthly": monthly,
    }


def increment_usage(
    user_id: str,
    timezone_name: str | None,
    counter: str,
    amount: int = 1,
):
    if counter not in USAGE_COUNTERS:
        raise ValueError(
            f"Unsupported usage counter: {counter}"
        )

    daily_period, monthly_period = (
        get_periods(timezone_name)
    )

    now = datetime.now(
        timezone.utc
    )

    # --------------------------------------------------------
    # DAILY
    # --------------------------------------------------------

    daily_result = (
        usage_tracking.find_one_and_update(
            {
                "user_id": user_id,
                "daily_period": daily_period,
            },
            {
                "$setOnInsert": {
                    "user_id": user_id,
                    "daily_period":
                        daily_period,
                    "created_at": now,
                },
                "$inc": {
                    counter: amount,
                },
                "$set": {
                    "updated_at": now,
                },
            },
            upsert=True,
            return_document=(
                ReturnDocument.AFTER
            ),
        )
    )

    # --------------------------------------------------------
    # MONTHLY
    # --------------------------------------------------------

    monthly_result = (
        monthly_usage.find_one_and_update(
            {
                "user_id": user_id,
                "monthly_period":
                    monthly_period,
            },
            {
                "$setOnInsert": {
                    "user_id": user_id,
                    "monthly_period":
                        monthly_period,
                    "created_at": now,
                },
                "$inc": {
                    counter: amount,
                },
                "$set": {
                    "updated_at": now,
                },
            },
            upsert=True,
            return_document=(
                ReturnDocument.AFTER
            ),
        )
    )

    return {
        "daily": daily_result,
        "monthly": monthly_result,
    }