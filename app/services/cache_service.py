from app.services.redis_service import r
from app.utils.hash_utils import hash_text

CACHE_TTL = 3600  # 1 hour


# 🔥 GENERATE UNIQUE CACHE KEY
def _make_key(
    user_id: str,
    question: str,
    doc_id: str = "",
    focus_mode: str = "balanced"
):

    raw = f"{question}:{doc_id}:{focus_mode}"

    q_hash = hash_text(raw)

    return f"cache:{user_id}:{q_hash}"


# 🔥 GET CACHE
def get_cached_response(
    user_id: str,
    question: str,
    doc_id: str = "",
    focus_mode: str = "balanced"
):

    try:

        key = _make_key(
            user_id,
            question,
            doc_id,
            focus_mode
        )

        return r.get(key)

    except Exception:

        return None


# 🔥 SAVE CACHE
def save_cache(
    user_id: str,
    question: str,
    response: str,
    doc_id: str = "",
    focus_mode: str = "balanced"
):

    try:

        key = _make_key(
            user_id,
            question,
            doc_id,
            focus_mode
        )

        r.setex(
            key,
            CACHE_TTL,
            response
        )

    except Exception:

        pass