# app/services/plan_service.py

from fastapi import HTTPException, status

from app.config.plans import PLANS
from app.services.usage_service import (
    get_usage
)


def get_plan(
    user
) -> str:

    plan = user.get(
        "plan",
        "free"
    )

    if plan not in PLANS:
        return "free"

    return plan


def get_plan_config(
    user
):
    return PLANS[
        get_plan(user)
    ]


def get_resource_limit(
    user,
    resource: str
) -> int:

    config = get_plan_config(user)

    return config["limits"].get(
        resource,
        0
    )


def get_usage_limit_status(
    user,
    counter: str
):

    plan_config = get_plan_config(user)

    limit_config = (
        plan_config["limits"]
        .get(counter)
    )

    if not limit_config:
        raise ValueError(
            f"No limit configured for {counter}"
        )

    usage = get_usage(
        str(user["_id"]),
        user.get(
            "timezone",
            "UTC"
        )
    )

    current = int(
        usage.get(counter, 0)
    )

    daily_limit = limit_config[
        "daily"
    ]

    monthly_limit = limit_config[
        "monthly"
    ]

    return {
        "used": current,
        "daily_limit": daily_limit,
        "monthly_limit": monthly_limit,
        "daily_remaining": max(
            0,
            daily_limit - current
        ),
        "monthly_remaining": max(
            0,
            monthly_limit - current
        ),
    }


def ensure_usage_available(
    user,
    counter: str,
    amount: int = 1
):

    status_data = get_usage_limit_status(
        user,
        counter
    )

    if (
        status_data["daily_remaining"]
        < amount
    ):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "code": "daily_limit_reached",
                "message":
                    "Daily limit reached.",
                "usage": status_data,
            }
        )

    if (
        status_data["monthly_remaining"]
        < amount
    ):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "code": "monthly_limit_reached",
                "message":
                    "Monthly limit reached.",
                "usage": status_data,
            }
        )

    return status_data


def build_limit_warning(
    user,
    counter: str
):

    status_data = get_usage_limit_status(
        user,
        counter
    )

    config = get_plan_config(user)

    threshold = config[
        "warning_threshold"
    ]

    daily_limit = status_data[
        "daily_limit"
    ]

    monthly_limit = status_data[
        "monthly_limit"
    ]

    daily_ratio = (
        status_data["daily_remaining"]
        / daily_limit
        if daily_limit > 0
        else 0
    )

    monthly_ratio = (
        status_data["monthly_remaining"]
        / monthly_limit
        if monthly_limit > 0
        else 0
    )

    warning = (
        daily_ratio <= threshold
        or monthly_ratio <= threshold
    )

    return {
        "warning": warning,
        "remaining_daily":
            status_data["daily_remaining"],
        "remaining_monthly":
            status_data["monthly_remaining"],
    }