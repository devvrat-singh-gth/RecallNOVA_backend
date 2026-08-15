# app/dependencies/auth.py

from fastapi import (
    Depends,
    HTTPException,
    status,
)
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.security import HTTPBearer
from jwt.exceptions import (
    ExpiredSignatureError,
    InvalidTokenError,
)

from app.db.mongo import users
from app.services.jwt_service import (
    decode_access_token
)
from bson import ObjectId


bearer_scheme = HTTPBearer(
    auto_error=False
)


def get_current_user(
    credentials:
        HTTPAuthorizationCredentials
        | None = Depends(bearer_scheme)
):

    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={
                "WWW-Authenticate":
                    "Bearer"
            }
        )

    if credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication scheme",
            headers={
                "WWW-Authenticate":
                    "Bearer"
            }
        )

    token = credentials.credentials

    try:

        payload = decode_access_token(
            token
        )

    except ExpiredSignatureError:

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Access token expired",
            headers={
                "WWW-Authenticate":
                    "Bearer"
            }
        )

    except InvalidTokenError:

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid access token",
            headers={
                "WWW-Authenticate":
                    "Bearer"
            }
        )

    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type"
        )

    user_id = payload.get("sub")

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token subject"
        )


    try:
        object_id = ObjectId(user_id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token subject"
        )

    user = users.find_one({
        "_id": object_id
    })

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )

    if user.get("disabled", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account disabled"
        )

    return user