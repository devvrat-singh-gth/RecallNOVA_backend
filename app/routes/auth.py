# app/routes/auth.py

import os
import secrets
from urllib.parse import quote
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    Response,
    status,
)
from fastapi.responses import RedirectResponse

from google.auth.transport import requests as google_requests
from google.oauth2 import id_token

from app.dependencies.auth import (
    get_current_user,
)

from app.schemas.auth import (
    EmailLoginRequest,
    EmailSignupRequest,
    ForgotPasswordRequest,
    GoogleLoginRequest,
    ResetPasswordRequest,
    TimezoneUpdateRequest,
    VerifyEmailRequest,
)

from app.services.auth_service import (
    create_email_user,
    create_password_reset_token,
    create_user,
    delete_user_by_id,
    find_user_by_email,
    find_user_by_google_id,
    get_user_by_id,
    reset_password,
    set_timezone,
    update_email_login,
    update_user_login,
    verify_email_token,
)

from app.services.email_service import (
    send_password_reset_email,
    send_verification_email,
)

from app.services.jwt_service import (
    create_access_token,
)

from app.services.password_service import (
    hash_password,
    verify_password,
)

from app.services.session_service import (
    create_refresh_session,
    get_session,
    revoke_session,
    revoke_all_user_sessions,
    rotate_session,
)


router = APIRouter()


# ============================================================
# CONFIGURATION
# ============================================================

GOOGLE_CLIENT_ID = os.getenv(
    "GOOGLE_CLIENT_ID"
)

if not GOOGLE_CLIENT_ID:
    raise RuntimeError(
        "GOOGLE_CLIENT_ID is not configured"
    )


FRONTEND_URL = os.getenv(
    "FRONTEND_URL"
)

if not FRONTEND_URL:
    raise RuntimeError(
        "FRONTEND_URL is not configured"
    )

FRONTEND_URL = FRONTEND_URL.rstrip("/")


EMAIL_VERIFY_PATH = os.getenv(
    "EMAIL_VERIFY_PATH",
    "/verify-email",
)

PASSWORD_RESET_PATH = os.getenv(
    "PASSWORD_RESET_PATH",
    "/reset-password",
)


REFRESH_COOKIE_NAME = (
    "recallnova_refresh"
)


COOKIE_SECURE = (
    os.getenv(
        "COOKIE_SECURE",
        "false",
    ).lower()
    == "true"
)


COOKIE_SAMESITE = (
    os.getenv(
        "COOKIE_SAMESITE",
        "lax",
    ).lower()
)


COOKIE_DOMAIN = os.getenv(
    "COOKIE_DOMAIN"
)

if COOKIE_DOMAIN:
    COOKIE_DOMAIN = COOKIE_DOMAIN.strip()


REFRESH_SESSION_DAYS = int(
    os.getenv(
        "REFRESH_SESSION_DAYS",
        "30",
    )
)


# ============================================================
# VALIDATION
# ============================================================

def validate_timezone(
    timezone_name: str | None,
) -> str:

    if not timezone_name:
        return "UTC"

    try:
        ZoneInfo(
            timezone_name
        )

        return timezone_name

    except ZoneInfoNotFoundError:
        return "UTC"


def validate_origin(
    request: Request,
):
    """
    Protect state-changing browser
    requests that rely on authentication
    cookies.

    The verification-link GET endpoint
    intentionally does not use this,
    because a user can legitimately arrive
    there directly from an email.
    """

    origin = request.headers.get(
        "origin"
    )

    if origin != FRONTEND_URL:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid request origin",
        )


# ============================================================
# USER SERIALIZATION
# ============================================================

def serialize_user(
    user,
):
    return {
        "id": str(
            user["_id"]
        ),

        "email": user[
            "email"
        ],

        "name": user.get(
            "name"
        ),

        "picture": user.get(
            "picture"
        ),

        "plan": user.get(
            "plan",
            "free",
        ),

        "timezone": user.get(
            "timezone",
            "UTC",
        ),
    }


# ============================================================
# SESSION/COKIE HELPERS
# ============================================================

def set_auth_cookies(
    response: Response,
    refresh_token: str,
):
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,

        value=refresh_token,

        max_age=(
            REFRESH_SESSION_DAYS
            * 24
            * 60
            * 60
        ),

        httponly=True,

        secure=COOKIE_SECURE,

        samesite=COOKIE_SAMESITE,

        domain=COOKIE_DOMAIN,

        path="/auth",
    )


def clear_auth_cookies(
    response: Response,
):
    response.delete_cookie(
        key=REFRESH_COOKIE_NAME,

        domain=COOKIE_DOMAIN,

        path="/auth",
    )


def create_authenticated_session(
    user,
    response: Response,
):
    session_id, refresh_token = (
        create_refresh_session(
            str(
                user["_id"]
            )
        )
    )

    access_token = (
        create_access_token(
            str(
                user["_id"]
            ),
            session_id,
        )
    )

    set_auth_cookies(
        response,
        refresh_token,
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": serialize_user(
            user
        ),
    }


# ============================================================
# GOOGLE LOGIN
# ============================================================

@router.post("/google")
def google_login(
    payload: GoogleLoginRequest,
    response: Response,
):
    try:
        google_info = (
            id_token.verify_oauth2_token(
                payload.google_token,

                google_requests.Request(),

                GOOGLE_CLIENT_ID,
            )
        )

    except ValueError:
        raise HTTPException(
            status_code=(
                status.HTTP_401_UNAUTHORIZED
            ),
            detail=(
                "Invalid Google identity token"
            ),
        )

    google_id = google_info.get(
        "sub"
    )

    email = (
        google_info.get(
            "email",
            "",
        )
        .lower()
        .strip()
    )

    if not google_id or not email:
        raise HTTPException(
            status_code=(
                status.HTTP_401_UNAUTHORIZED
            ),
            detail=(
                "Google account information "
                "incomplete"
            ),
        )

    if not google_info.get(
        "email_verified",
        False,
    ):
        raise HTTPException(
            status_code=(
                status.HTTP_401_UNAUTHORIZED
            ),
            detail=(
                "Google email is not verified"
            ),
        )

    timezone_name = (
        validate_timezone(
            payload.timezone
        )
    )

    # --------------------------------------------------------
    # FIND GOOGLE USER
    # --------------------------------------------------------

    user = find_user_by_google_id(
        google_id
    )

    # --------------------------------------------------------
    # CREATE GOOGLE USER
    # --------------------------------------------------------

    if not user:

        existing_email_user = (
            find_user_by_email(
                email
            )
        )

        if existing_email_user:
            raise HTTPException(
                status_code=(
                    status.HTTP_409_CONFLICT
                ),
                detail=(
                    "An account with this email "
                    "already exists. Sign in using "
                    "the method originally used to "
                    "create the account."
                ),
            )

        user = create_user(
            google_id=google_id,

            email=email,

            name=google_info.get(
                "name"
            ),

            picture=google_info.get(
                "picture"
            ),

            timezone_name=timezone_name,
        )

    # --------------------------------------------------------
    # EXISTING GOOGLE USER
    # --------------------------------------------------------

    else:
        user = update_user_login(
            user_id=user["_id"],

            name=google_info.get(
                "name"
            ),

            picture=google_info.get(
                "picture"
            ),

            timezone_name=timezone_name,
        )

    return create_authenticated_session(
        user,
        response,
    )


# ============================================================
# EMAIL SIGNUP
# ============================================================

@router.post("/email/signup")
def email_signup(
    payload: EmailSignupRequest,
    request: Request,
    response: Response,
):
    validate_origin(
        request
    )

    email = str(
        payload.email
    ).lower().strip()

    timezone_name = (
        validate_timezone(
            payload.timezone
        )
    )

    existing_user = (
        find_user_by_email(
            email
        )
    )

    if existing_user:
        raise HTTPException(
            status_code=(
                status.HTTP_409_CONFLICT
            ),
            detail=(
                "An account with this email "
                "already exists."
            ),
        )

    verification_token = (
        secrets.token_urlsafe(48)
    )

    password_hash = (
        hash_password(
            payload.password
        )
    )

    try:
        user = create_email_user(
            email=email,

            password_hash=password_hash,

            name=payload.name,

            timezone_name=timezone_name,

            verification_token=
                verification_token,
        )

    except Exception:
        raise HTTPException(
            status_code=500,
            detail=(
                "Unable to create account."
            ),
        )

    verification_url = (
        f"{FRONTEND_URL}"
        f"{EMAIL_VERIFY_PATH}"
        f"?token="
        f"{quote(verification_token)}"
    )

    try:
        send_verification_email(
            email,
            verification_url,
        )

    except Exception as exc:
        delete_user_by_id(
            str(
                user["_id"]
            )
        )

        raise HTTPException(
            status_code=503,
            detail=(
                "Unable to send verification "
                "email. Please try again."
            ),
        ) from exc

    return {
        "success": True,

        "message": (
            "Account created. "
            "Please check your email "
            "to verify your account."
        ),
    }


# ============================================================
# EMAIL LOGIN
# ============================================================

@router.post("/email/login")
def email_login(
    payload: EmailLoginRequest,
    request: Request,
    response: Response,
):
    validate_origin(
        request
    )

    email = str(
        payload.email
    ).lower().strip()

    user = find_user_by_email(
        email
    )

    if not user:
        raise HTTPException(
            status_code=(
                status.HTTP_401_UNAUTHORIZED
            ),
            detail=(
                "Invalid email or password."
            ),
        )

    if user.get(
        "disabled",
        False,
    ):
        raise HTTPException(
            status_code=(
                status.HTTP_403_FORBIDDEN
            ),
            detail="Account disabled.",
        )

    password_hash = user.get(
        "password_hash"
    )

    if not password_hash:
        raise HTTPException(
            status_code=(
                status.HTTP_401_UNAUTHORIZED
            ),
            detail=(
                "This account uses Google "
                "sign-in. Please continue "
                "with Google."
            ),
        )

    if not verify_password(
        payload.password,
        password_hash,
    ):
        raise HTTPException(
            status_code=(
                status.HTTP_401_UNAUTHORIZED
            ),
            detail=(
                "Invalid email or password."
            ),
        )

    if not user.get(
        "email_verified",
        False,
    ):
        raise HTTPException(
            status_code=(
                status.HTTP_403_FORBIDDEN
            ),
            detail=(
                "Please verify your email "
                "before signing in."
            ),
        )

    user = update_email_login(
        str(
            user["_id"]
        )
    )

    return create_authenticated_session(
        user,
        response,
    )


# ============================================================
# EMAIL VERIFICATION — API
# ============================================================

@router.post("/email/verify")
def verify_email(
    payload: VerifyEmailRequest,
    request: Request,
):
    validate_origin(
        request
    )

    user = verify_email_token(
        payload.token
    )

    if not user:
        raise HTTPException(
            status_code=400,
            detail=(
                "Verification link is "
                "invalid or expired."
            ),
        )

    return {
        "success": True,

        "message": (
            "Email verified successfully."
        ),
    }


# ============================================================
# EMAIL VERIFICATION — BROWSER LINK
# ============================================================

@router.get("/email/verify")
def verify_email_from_link(
    token: str,
):
    user = verify_email_token(
        token
    )

    if user:
        return RedirectResponse(
            url=(
                f"{FRONTEND_URL}"
                f"{EMAIL_VERIFY_PATH}"
                "?status=success"
            ),
            status_code=303,
        )

    return RedirectResponse(
        url=(
            f"{FRONTEND_URL}"
            f"{EMAIL_VERIFY_PATH}"
            "?status=error"
        ),
        status_code=303,
    )


# ============================================================
# FORGOT PASSWORD
# ============================================================

@router.post("/email/forgot-password")
def forgot_password(
    payload: ForgotPasswordRequest,
    request: Request,
):
    validate_origin(
        request
    )

    email = str(
        payload.email
    ).lower().strip()

    user = find_user_by_email(
        email
    )

    # Always return the same response so
    # this endpoint does not reveal whether
    # a particular email exists.
    generic_response = {
        "success": True,

        "message": (
            "If an account exists for this "
            "email, a password reset link "
            "has been sent."
        ),
    }

    if not user:
        return generic_response

    if not user.get(
        "password_hash"
    ):
        return generic_response

    reset_token = (
        secrets.token_urlsafe(48)
    )

    create_password_reset_token(
        str(
            user["_id"]
        ),
        reset_token,
    )

    reset_url = (
        f"{FRONTEND_URL}"
        f"{PASSWORD_RESET_PATH}"
        f"?token="
        f"{quote(reset_token)}"
    )

    try:
        send_password_reset_email(
            email,
            reset_url,
        )

    except Exception:
        # Do not expose provider details.
        # The endpoint still returns the
        # generic response.
        return generic_response

    return generic_response


# ============================================================
# RESET PASSWORD
# ============================================================

@router.post("/email/reset-password")
def reset_password_route(
    payload: ResetPasswordRequest,
    request: Request,
):
    validate_origin(
        request
    )

    password_hash = (
        hash_password(
            payload.password
        )
    )

    user = reset_password(
        payload.token,
        password_hash,
    )

    if not user:
        raise HTTPException(
            status_code=400,
            detail=(
                "Password reset link is "
                "invalid or expired."
            ),
        )

    # Password reset is a security event.
    # Kill all existing persistent sessions.
    revoke_all_user_sessions(
        str(
            user["_id"]
        )
    )

    return {
        "success": True,

        "message": (
            "Password reset successfully. "
            "Please sign in again."
        ),
    }


# ============================================================
# REFRESH ACCESS TOKEN
# ============================================================

@router.post("/refresh")
def refresh_access_token(
    request: Request,
    response: Response,
):
    validate_origin(
        request
    )

    raw_refresh_token = (
        request.cookies.get(
            REFRESH_COOKIE_NAME
        )
    )

    if not raw_refresh_token:
        raise HTTPException(
            status_code=(
                status.HTTP_401_UNAUTHORIZED
            ),
            detail=(
                "Refresh session missing"
            ),
        )

    session = get_session(
        raw_refresh_token
    )

    if not session:
        clear_auth_cookies(
            response
        )

        raise HTTPException(
            status_code=(
                status.HTTP_401_UNAUTHORIZED
            ),
            detail=(
                "Refresh session expired "
                "or revoked"
            ),
        )

    user = get_user_by_id(
        session["user_id"]
    )

    if (
        not user
        or user.get(
            "disabled",
            False,
        )
    ):
        revoke_session(
            raw_refresh_token
        )

        clear_auth_cookies(
            response
        )

        raise HTTPException(
            status_code=(
                status.HTTP_401_UNAUTHORIZED
            ),
            detail=(
                "Account unavailable"
            ),
        )

    rotated = rotate_session(
        raw_refresh_token,
        session["user_id"],
    )

    if not rotated:
        clear_auth_cookies(
            response
        )

        raise HTTPException(
            status_code=(
                status.HTTP_401_UNAUTHORIZED
            ),
            detail=(
                "Refresh session invalid"
            ),
        )

    (
        session_id,
        new_refresh_token,
    ) = rotated

    access_token = (
        create_access_token(
            session["user_id"],
            session_id,
        )
    )

    set_auth_cookies(
        response,
        new_refresh_token,
    )

    return {
        "access_token": access_token,

        "token_type": "bearer",

        "user": serialize_user(
            user
        ),
    }


# ============================================================
# LOGOUT
# ============================================================

@router.post("/logout")
def logout(
    request: Request,
    response: Response,
):
    validate_origin(
        request
    )

    raw_refresh_token = (
        request.cookies.get(
            REFRESH_COOKIE_NAME
        )
    )

    if raw_refresh_token:
        revoke_session(
            raw_refresh_token
        )

    clear_auth_cookies(
        response
    )

    return {
        "success": True
    }


# ============================================================
# CURRENT USER
# ============================================================

@router.get("/me")
def get_me(
    current_user=Depends(
        get_current_user
    ),
):
    return {
        "user": serialize_user(
            current_user
        )
    }


# ============================================================
# TIMEZONE
# ============================================================

@router.patch("/timezone")
def update_timezone(
    payload: TimezoneUpdateRequest,
    current_user=Depends(
        get_current_user
    ),
):
    timezone_name = (
        validate_timezone(
            payload.timezone
        )
    )

    user = set_timezone(
        str(
            current_user["_id"]
        ),
        timezone_name,
    )

    return {
        "user": serialize_user(
            user
        )
    }