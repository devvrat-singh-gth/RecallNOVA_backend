# app/services/auth_service.py

from datetime import datetime, timezone
from typing import Optional

from bson import ObjectId

from app.db.mongo import users
from app.services.verification_service import (
    get_token_expiry,
    hash_token,
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
    now = datetime.now(
        timezone.utc
    )

    email = normalize_email(
        email
    )

    result = users.insert_one(
        {
            "google_id": google_id,
            "email": email,
            "name": name,
            "picture": picture,

            "auth_provider": "google",

            "password_hash": None,

            # Google has already verified
            # ownership of the email address.
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

                # Google identity remains
                # verified.
                "email_verified": True,
                "auth_provider": "google",
            }
        },
    )

    return get_user_by_id(
        str(user_id)
    )


# ============================================================
# EMAIL USER CREATION
# ============================================================

def create_email_user(
    email: str,
    password_hash: str,
    name: Optional[str],
    timezone_name: str,
    verification_token: str,
):
    now = datetime.now(
        timezone.utc
    )

    email = normalize_email(
        email
    )

    verification_hash = hash_token(
        verification_token
    )

    verification_expires = (
        get_token_expiry()
    )

    result = users.insert_one(
        {
            # Do not store google_id=None.
            # The field should simply be absent
            # for an email-authenticated user.

            "email": email,

            "name": name,

            "picture": None,

            "auth_provider": "email",

            "password_hash": password_hash,

            "email_verified": False,

            "verification_token_hash":
                verification_hash,

            "verification_expires_at":
                verification_expires,

            # These fields are intentionally
            # omitted until a reset is requested.

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


def delete_user_by_id(
    user_id: str,
):
    try:
        object_id = ObjectId(
            user_id
        )

    except Exception:
        return False

    result = users.delete_one(
        {
            "_id": object_id,
        }
    )

    return (
        result.deleted_count > 0
    )


# ============================================================
# EMAIL VERIFICATION
# ============================================================

def verify_email_token(
    token: str,
):
    now = datetime.now(
        timezone.utc
    )

    token_hash = hash_token(
        token
    )

    user = users.find_one(
        {
            "verification_token_hash":
                token_hash,

            "verification_expires_at": {
                "$gt": now,
            },

            "email_verified": False,
        }
    )

    if not user:
        return None

    users.update_one(
        {
            "_id": user["_id"],
        },
        {
            "$set": {
                "email_verified": True,
                "updated_at": now,
            },
            "$unset": {
                "verification_token_hash": "",
                "verification_expires_at": "",
            },
        },
    )

    return get_user_by_id(
        str(user["_id"])
    )


# ============================================================
# PASSWORD RESET TOKEN
# ============================================================

def create_password_reset_token(
    user_id: str,
    reset_token: str,
):
    now = datetime.now(
        timezone.utc
    )

    try:
        object_id = ObjectId(
            user_id
        )
    except Exception:
        raise ValueError(
            "Invalid user id"
        )

    reset_hash = hash_token(
        reset_token
    )

    expires_at = get_token_expiry()

    users.update_one(
        {
            "_id": object_id,
        },
        {
            "$set": {
                "password_reset_token_hash":
                    reset_hash,

                "password_reset_expires_at":
                    expires_at,

                "updated_at": now,
            },
        },
    )


def reset_password(
    token: str,
    password_hash: str,
):
    now = datetime.now(
        timezone.utc
    )

    token_hash = hash_token(
        token
    )

    user = users.find_one(
        {
            "password_reset_token_hash":
                token_hash,

            "password_reset_expires_at": {
                "$gt": now,
            },
        }
    )

    if not user:
        return None

    users.update_one(
        {
            "_id": user["_id"],
        },
        {
            "$set": {
                "password_hash":
                    password_hash,

                "auth_provider": "email",

                "updated_at": now,
            },

            "$unset": {
                "password_reset_token_hash": "",
                "password_reset_expires_at": "",
            },
        },
    )

    return get_user_by_id(
        str(user["_id"])
    )


# ============================================================
# LOGIN METADATA
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
            },
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