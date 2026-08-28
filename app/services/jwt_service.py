# app/services/jwt_service.py

import os
from datetime import (
    datetime,
    timedelta,
    timezone,
)
from typing import Any

import jwt


JWT_SECRET = os.getenv(
    "JWT_SECRET"
)

if not JWT_SECRET:
    raise RuntimeError(
        "JWT_SECRET is not configured"
    )


JWT_ALGORITHM = os.getenv(
    "JWT_ALGORITHM",
    "HS256",
)


ACCESS_TOKEN_MINUTES = int(
    os.getenv(
        "ACCESS_TOKEN_MINUTES",
        "15",
    )
)


GUEST_TOKEN_MINUTES = int(
    os.getenv(
        "GUEST_TOKEN_MINUTES",
        str(60 * 24 * 7),  # 7 days
    )
)


JWT_ISSUER = os.getenv(
    "JWT_ISSUER",
    "recallnova-api",
)


JWT_AUDIENCE = os.getenv(
    "JWT_AUDIENCE",
    "recallnova-web",
)


def _create_token(
    *,
    subject: str,
    token_type: str,
    session_id: str | None,
    expires_minutes: int,
    timezone_name: str = "UTC",
):
    now = datetime.now(
        timezone.utc
    )

    payload = {
        "sub": subject,

        "sid":
            session_id
            if session_id
            else subject,

        "type":
            token_type,

        "timezone":
            timezone_name,

        "iss":
            JWT_ISSUER,

        "aud":
            JWT_AUDIENCE,

        "iat":
            now,

        "exp":
            now + timedelta(
                minutes=expires_minutes
            ),
    }

    return jwt.encode(
        payload,
        JWT_SECRET,
        algorithm=JWT_ALGORITHM,
    )


def create_access_token(
    user_id: str,
    session_id: str,
) -> str:

    return _create_token(
        subject=user_id,
        token_type="access",
        session_id=session_id,
        expires_minutes=(
            ACCESS_TOKEN_MINUTES
        ),
    )


def create_guest_access_token(
    guest_id: str,
    timezone_name: str = "UTC",
) -> str:

    return _create_token(
        subject=guest_id,
        token_type="guest",
        session_id=None,
        expires_minutes=(
            GUEST_TOKEN_MINUTES
        ),
        timezone_name=timezone_name,
    )


def decode_token(
    token: str,
) -> dict[str, Any]:

    return jwt.decode(
        token,
        JWT_SECRET,
        algorithms=[
            JWT_ALGORITHM
        ],
        issuer=JWT_ISSUER,
        audience=JWT_AUDIENCE,
        leeway=30,
        options={
            "require": [
                "sub",
                "sid",
                "type",
                "iss",
                "aud",
                "iat",
                "exp",
            ]
        },
    )


def decode_access_token(
    token: str,
) -> dict[str, Any]:

    payload = decode_token(
        token
    )

    if payload.get(
        "type"
    ) != "access":
        raise jwt.InvalidTokenError(
            "Invalid access token type"
        )

    return payload