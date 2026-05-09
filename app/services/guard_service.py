from app.services.redis_service import r

MAX_REQUESTS = 10
WINDOW = 60  # seconds
MAX_INPUT_CHARS = 2000


def check_rate_limit(user_id: str):
    key = f"rate:{user_id}"

    try:
        current = r.get(key)

        if current and int(current) >= MAX_REQUESTS:
            return False

        pipe = r.pipeline()
        pipe.incr(key)
        pipe.expire(key, WINDOW)
        pipe.execute()

        return True

    except Exception:
        # fallback → allow request (don’t break app)
        return True


def token_guard(text: str):
    return text[:MAX_INPUT_CHARS]