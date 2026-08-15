# app/services/verification_service.py

import hashlib
import os
import secrets
from datetime import datetime, timedelta, timezone


EMAIL_TOKEN_MINUTES = int(
    os.getenv(
        "EMAIL_TOKEN_MINUTES",
        "30",
    )
)


def generate_secure_token(
    length: int = 48,
) -> str:
    """
    Generate a cryptographically secure,
    URL-safe token.

    The raw token is sent only through
    the verification/reset email.
    MongoDB stores only its hash.
    """

    if length < 16:
        length = 16

    return secrets.token_urlsafe(
        length
    )


def hash_token(
    token: str,
) -> str:
    """
    SHA-256 hash for verification/reset
    tokens stored in MongoDB.
    """

    return hashlib.sha256(
        token.encode("utf-8")
    ).hexdigest()


def get_token_expiry(
    minutes: int | None = None,
) -> datetime:
    """
    Return an absolute UTC expiration
    timestamp for an auth token.
    """

    lifetime = (
        minutes
        if minutes is not None
        else EMAIL_TOKEN_MINUTES
    )

    return (
        datetime.now(timezone.utc)
        + timedelta(
            minutes=lifetime
        )
    )


def token_is_expired(
    expires_at,
) -> bool:
    """
    Safely determine whether a token
    expiration timestamp has passed.
    """

    if not expires_at:
        return True

    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(
            tzinfo=timezone.utc
        )

    return (
        expires_at
        <= datetime.now(timezone.utc)
    )