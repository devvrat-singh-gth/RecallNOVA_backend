# app/dependencies/auth.py

from bson import ObjectId

from fastapi import (
    Depends,
    HTTPException,
    status,
)

from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer,
)

from jwt.exceptions import (
    ExpiredSignatureError,
    InvalidTokenError,
)

from app.db.mongo import users

from app.services.jwt_service import (
    decode_token,
)


bearer_scheme = HTTPBearer(
    auto_error=False
)


def _get_credentials(
    credentials,
):
    if not credentials:
        raise HTTPException(
            status_code=(
                status.HTTP_401_UNAUTHORIZED
            ),
            detail="Authentication required",
            headers={
                "WWW-Authenticate":
                    "Bearer"
            },
        )

    if (
        credentials.scheme.lower()
        != "bearer"
    ):
        raise HTTPException(
            status_code=(
                status.HTTP_401_UNAUTHORIZED
            ),
            detail="Invalid authentication scheme",
            headers={
                "WWW-Authenticate":
                    "Bearer"
            },
        )

    return credentials.credentials


def get_current_identity(
    credentials:
        HTTPAuthorizationCredentials
        | None = Depends(
            bearer_scheme
        ),
):
    token = _get_credentials(
        credentials
    )

    try:
        payload = decode_token(
            token
        )

    except ExpiredSignatureError:
        raise HTTPException(
            status_code=(
                status.HTTP_401_UNAUTHORIZED
            ),
            detail="Session expired",
            headers={
                "WWW-Authenticate":
                    "Bearer"
            },
        )

    except InvalidTokenError:
        raise HTTPException(
            status_code=(
                status.HTTP_401_UNAUTHORIZED
            ),
            detail="Invalid authentication token",
            headers={
                "WWW-Authenticate":
                    "Bearer"
            },
        )

    token_type = payload.get(
        "type"
    )

    # ========================================================
    # REGISTERED USER
    # ========================================================

    if token_type == "access":

        user_id = payload.get(
            "sub"
        )

        if not user_id:
            raise HTTPException(
                status_code=(
                    status.HTTP_401_UNAUTHORIZED
                ),
                detail="Invalid token subject",
            )

        try:
            object_id = ObjectId(
                user_id
            )
        except Exception:
            raise HTTPException(
                status_code=(
                    status.HTTP_401_UNAUTHORIZED
                ),
                detail="Invalid token subject",
            )

        user = users.find_one(
            {
                "_id": object_id
            }
        )

        if not user:
            raise HTTPException(
                status_code=(
                    status.HTTP_401_UNAUTHORIZED
                ),
                detail="User not found",
            )

        if user.get(
            "disabled",
            False,
        ):
            raise HTTPException(
                status_code=(
                    status.HTTP_403_FORBIDDEN
                ),
                detail="Account disabled",
            )

        user["is_guest"] = False

        return user

    # ========================================================
    # GUEST
    # ========================================================

    if token_type == "guest":

        guest_id = payload.get(
            "sub"
        )

        if not guest_id:
            raise HTTPException(
                status_code=(
                    status.HTTP_401_UNAUTHORIZED
                ),
                detail="Invalid guest session",
            )

        return {
            "_id": guest_id,

            "email": "",

            "name": "Guest",

            "picture": None,

            "plan": "guest",

            "timezone":
                payload.get(
                    "timezone",
                    "UTC",
                ),

            "disabled": False,

            "is_guest": True,
        }

    raise HTTPException(
        status_code=(
            status.HTTP_401_UNAUTHORIZED
        ),
        detail="Invalid token type",
    )


def get_current_user(
    credentials:
        HTTPAuthorizationCredentials
        | None = Depends(
            bearer_scheme
        ),
):
    identity = get_current_identity(
        credentials
    )

    if identity.get(
        "is_guest",
        False,
    ):
        raise HTTPException(
            status_code=(
                status.HTTP_403_FORBIDDEN
            ),
            detail=(
                "This action requires a registered account."
            ),
        )

    return identity