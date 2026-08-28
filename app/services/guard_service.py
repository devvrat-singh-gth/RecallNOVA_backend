# app/services/guard_service.py

from app.config.plans import PLANS
from app.services.redis_service import r


WINDOW = 60  # seconds

MAX_INPUT_CHARS = 2000


def get_rate_limit(
    plan: str,
) -> int:

    config = PLANS.get(
        plan,
        PLANS["free"],
    )

    return int(
        config.get(
            "rate_limit_per_minute",
            10,
        )
    )


def check_rate_limit(
    identity_id: str,
    plan: str = "free",
) -> bool:

    try:
        if not r:
            return True

        limit = get_rate_limit(
            plan
        )

        key = (
            f"rate:"
            f"{plan}:"
            f"{identity_id}"
        )

        current = r.incr(
            key
        )

        if current == 1:
            r.expire(
                key,
                WINDOW,
            )

        return current <= limit

    except Exception:
        # Redis should never bring
        # down the application.
        return True


def token_guard(
    text: str,
):
    return text[
        :MAX_INPUT_CHARS
    ]