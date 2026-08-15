# app/services/usage_service.py

from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.db.mongo import usage_tracking


USAGE_COUNTERS = (
    "messages",
    "flashcard_generations",
    "quiz_generations",
)


def get_valid_timezone(
    timezone_name: str | None
) -> ZoneInfo:

    if not timezone_name:
        return ZoneInfo("UTC")

    try:
        return ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError:
        return ZoneInfo("UTC")


def get_periods(
    timezone_name: str | None
):
    tz = get_valid_timezone(
        timezone_name
    )

    local_now = datetime.now(
        timezone.utc
    ).astimezone(tz)

    return (
        local_now.strftime("%Y-%m-%d"),
        local_now.strftime("%Y-%m")
    )


def get_usage_document(
    user_id: str,
    timezone_name: str | None
):

    daily_period, monthly_period = (
        get_periods(timezone_name)
    )

    document = usage_tracking.find_one({
        "user_id": user_id,
        "daily_period": daily_period,
        "monthly_period": monthly_period,
    })

    if document:
        return document

    return {
        "user_id": user_id,
        "daily_period": daily_period,
        "monthly_period": monthly_period,
        "messages": 0,
        "flashcard_generations": 0,
        "quiz_generations": 0,
    }


def increment_usage(
    user_id: str,
    timezone_name: str | None,
    counter: str,
    amount: int = 1
):

    if counter not in USAGE_COUNTERS:
        raise ValueError(
            f"Unsupported usage counter: {counter}"
        )

    daily_period, monthly_period = (
        get_periods(timezone_name)
    )

    result = usage_tracking.find_one_and_update(
        {
            "user_id": user_id,
            "daily_period": daily_period,
            "monthly_period": monthly_period,
        },
        {
            "$setOnInsert": {
                "user_id": user_id,
                "daily_period": daily_period,
                "monthly_period": monthly_period,
            },
            "$inc": {
                counter: amount
            }
        },
        upsert=True,
        return_document=__import__(
            "pymongo"
        ).ReturnDocument.AFTER
    )

    return result


def get_usage(
    user_id: str,
    timezone_name: str | None
):

    return get_usage_document(
        user_id,
        timezone_name
    )