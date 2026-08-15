# app/services/session_service.py

import hashlib
import os
import secrets
from datetime import datetime, timedelta, timezone

from pymongo import ReturnDocument

from app.db.mongo import auth_sessions


REFRESH_SESSION_DAYS = int(
    os.getenv(
        "REFRESH_SESSION_DAYS",
        "30",
    )
)


# ============================================================
# TOKEN HASHING
# ============================================================

def hash_token(
    token: str,
) -> str:
    return hashlib.sha256(
        token.encode("utf-8")
    ).hexdigest()


# ============================================================
# CREATE SESSION
# ============================================================

def create_refresh_session(
    user_id: str,
):
    raw_token = secrets.token_urlsafe(
        64
    )

    now = datetime.now(
        timezone.utc
    )

    session_id = secrets.token_urlsafe(
        32
    )

    auth_sessions.insert_one(
        {
            "session_id": session_id,

            "user_id": user_id,

            "token_hash":
                hash_token(
                    raw_token
                ),

            "created_at": now,

            "last_used_at": now,

            "expires_at": (
                now
                + timedelta(
                    days=REFRESH_SESSION_DAYS
                )
            ),

            "revoked": False,

            "revoked_at": None,
        }
    )

    return (
        session_id,
        raw_token,
    )


# ============================================================
# GET SESSION
# ============================================================

def get_session(
    raw_token: str,
):
    """
    Validate an active refresh token.

    The raw token is never stored in MongoDB.
    Only its SHA-256 hash is stored.
    """

    now = datetime.now(
        timezone.utc
    )

    return auth_sessions.find_one_and_update(
        {
            "token_hash":
                hash_token(
                    raw_token
                ),

            "revoked": False,

            "expires_at": {
                "$gt": now,
            },
        },
        {
            "$set": {
                "last_used_at": now,
            }
        },
        return_document=ReturnDocument.AFTER,
    )


# ============================================================
# ROTATE REFRESH TOKEN
# ============================================================

def rotate_session(
    old_raw_token: str,
    user_id: str,
):
    """
    Rotate the refresh credential while
    preserving the same MongoDB session.

    One login:
        session_id = A

    refresh:
        session_id = A
        token hash changes

    refresh again:
        session_id = A
        token hash changes again

    This avoids creating a new MongoDB
    session document on every refresh.
    """

    old_hash = hash_token(
        old_raw_token
    )

    new_refresh_token = (
        secrets.token_urlsafe(64)
    )

    new_hash = hash_token(
        new_refresh_token
    )

    now = datetime.now(
        timezone.utc
    )

    session = (
        auth_sessions.find_one_and_update(
            {
                "token_hash": old_hash,

                "user_id": user_id,

                "revoked": False,

                "expires_at": {
                    "$gt": now,
                },
            },
            {
                "$set": {
                    "token_hash":
                        new_hash,

                    "last_used_at":
                        now,

                    "rotated_at":
                        now,
                }
            },
            return_document=ReturnDocument.AFTER,
        )
    )

    if not session:
        return None

    return (
        session["session_id"],
        new_refresh_token,
    )


# ============================================================
# REVOKE ONE SESSION
# ============================================================

def revoke_session(
    raw_token: str,
):
    result = auth_sessions.update_one(
        {
            "token_hash":
                hash_token(
                    raw_token
                ),

            "revoked": False,
        },
        {
            "$set": {
                "revoked": True,

                "revoked_at":
                    datetime.now(
                        timezone.utc
                    ),
            }
        },
    )

    return (
        result.modified_count > 0
    )


# ============================================================
# REVOKE ALL SESSIONS
# ============================================================

def revoke_all_user_sessions(
    user_id: str,
):
    return auth_sessions.update_many(
        {
            "user_id": user_id,

            "revoked": False,
        },
        {
            "$set": {
                "revoked": True,

                "revoked_at":
                    datetime.now(
                        timezone.utc
                    ),
            }
        },
    )