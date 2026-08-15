# app/services/jwt_service.py

import os
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt


JWT_SECRET = os.getenv("JWT_SECRET")

if not JWT_SECRET:
    raise RuntimeError(
        "JWT_SECRET is not configured"
    )

JWT_ALGORITHM = os.getenv(
    "JWT_ALGORITHM",
    "HS256"
)

ACCESS_TOKEN_MINUTES = int(
    os.getenv(
        "ACCESS_TOKEN_MINUTES",
        "15"
    )
)

JWT_ISSUER = os.getenv(
    "JWT_ISSUER",
    "recallnova-api"
)

JWT_AUDIENCE = os.getenv(
    "JWT_AUDIENCE",
    "recallnova-web"
)


def create_access_token(
    user_id: str,
    session_id: str
) -> str:

    now = datetime.now(timezone.utc)

    payload = {
        "sub": user_id,
        "sid": session_id,
        "type": "access",
        "iss": JWT_ISSUER,
        "aud": JWT_AUDIENCE,
        "iat": now,
        "exp": now + timedelta(
            minutes=ACCESS_TOKEN_MINUTES
        ),
    }

    return jwt.encode(
        payload,
        JWT_SECRET,
        algorithm=JWT_ALGORITHM
    )


def decode_access_token(
    token: str
) -> dict[str, Any]:

    return jwt.decode(
        token,
        JWT_SECRET,
        algorithms=[JWT_ALGORITHM],
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