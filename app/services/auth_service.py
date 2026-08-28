# app/services/auth_service.py

from datetime import datetime, timezone
from typing import Optional

from bson import ObjectId

from app.db.mongo import (
    users,
    documents,
    chat_sessions,
    flashcards,
    quizzes,
    quiz_progress,
)
# ============================================================
# HELPERS
# ============================================================

def normalize_email(
    email: str,
) -> str:
    return email.lower().strip()


# ============================================================
# LOOKUPS
# ============================================================

def find_user_by_google_id(
    google_id: str,
):
    return users.find_one(
        {
            "google_id": google_id,
        }
    )


def find_user_by_email(
    email: str,
):
    return users.find_one(
        {
            "email": normalize_email(email),
        }
    )


def get_user_by_id(
    user_id: str,
):
    try:
        object_id = ObjectId(user_id)

    except Exception:
        return None

    return users.find_one(
        {
            "_id": object_id,
        }
    )


# ============================================================
# GOOGLE USER
# ============================================================

def create_user(
    google_id: str,
    email: str,
    name: Optional[str],
    picture: Optional[str],
    timezone_name: str,
):
    now = datetime.now(timezone.utc)

    normalized_email = normalize_email(
        email
    )

    result = users.insert_one(
        {
            "google_id": google_id,

            "email": normalized_email,

            "name": name,

            "picture": picture,

            "auth_provider": "google",

            "password_hash": None,

            "email_verified": True,

            "plan": "free",

            "timezone": timezone_name,

            "disabled": False,

            "created_at": now,

            "updated_at": now,

            "last_login_at": now,
        }
    )

    return users.find_one(
        {
            "_id": result.inserted_id,
        }
    )


def update_user_login(
    user_id: ObjectId,
    name: Optional[str],
    picture: Optional[str],
    timezone_name: str,
):
    now = datetime.now(
        timezone.utc
    )

    users.update_one(
        {
            "_id": user_id,
        },
        {
            "$set": {
                "name": name,

                "picture": picture,

                "timezone": timezone_name,

                "updated_at": now,

                "last_login_at": now,

                "email_verified": True,

                "auth_provider": "google",
            }
        },
    )

    return get_user_by_id(
        str(user_id)
    )


# ============================================================
# NATIVE EMAIL USER
# ============================================================

def create_email_user(
    email: str,
    password_hash: str,
    name: Optional[str],
    timezone_name: str,
):
    now = datetime.now(
        timezone.utc
    )

    normalized_email = normalize_email(
        email
    )

    result = users.insert_one(
        {
            "email": normalized_email,

            "name": name,

            "picture": None,

            "auth_provider": "email",

            "password_hash": password_hash,

            # Native accounts don't require
            # email verification.
            "email_verified": True,

            "plan": "free",

            "timezone": timezone_name,

            "disabled": False,

            "created_at": now,

            "updated_at": now,

            "last_login_at": None,
        }
    )

    return users.find_one(
        {
            "_id": result.inserted_id,
        }
    )


# ============================================================
# EMAIL LOGIN METADATA
# ============================================================

def update_email_login(
    user_id: str,
):
    now = datetime.now(
        timezone.utc
    )

    users.update_one(
        {
            "_id": ObjectId(user_id),
        },
        {
            "$set": {
                "last_login_at": now,

                "updated_at": now,
            }
        },
    )

    return get_user_by_id(
        user_id
    )


# ============================================================
# TIMEZONE
# ============================================================

def set_timezone(
    user_id: str,
    timezone_name: str,
):
    users.update_one(
        {
            "_id": ObjectId(user_id),
        },
        {
            "$set": {
                "timezone": timezone_name,

                "updated_at":
                    datetime.now(
                        timezone.utc
                    ),
            }
        },
    )

    return get_user_by_id(
        user_id
    )

def migrate_guest_data(
    guest_id: str,
    user_id: str,
):
    collections = [
        documents,
        chat_sessions,
        flashcards,
        quizzes,
        quiz_progress,
    ]

    for collection in collections:

        collection.update_many(
            {
                "user_id": guest_id
            },
            {
                "$set": {
                    "user_id": user_id,
                    "guest_data": False
                }
            }
        )