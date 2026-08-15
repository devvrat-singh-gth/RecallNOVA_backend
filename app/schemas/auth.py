# app/schemas/auth.py

from typing import Optional

from pydantic import (
    BaseModel,
    EmailStr,
    Field,
)


# ============================================================
# GOOGLE AUTH
# ============================================================

class GoogleLoginRequest(BaseModel):
    google_token: str = Field(
        min_length=1,
    )

    timezone: Optional[str] = None


# ============================================================
# GENERAL AUTH
# ============================================================

class TimezoneUpdateRequest(BaseModel):
    timezone: str = Field(
        min_length=1,
    )


class UserResponse(BaseModel):
    id: str
    email: str
    name: Optional[str] = None
    picture: Optional[str] = None
    plan: str
    timezone: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse


# ============================================================
# USAGE
# ============================================================

class UsageResponse(BaseModel):
    messages: dict
    flashcard_generations: dict
    quiz_generations: dict


# ============================================================
# EMAIL AUTH
# ============================================================

class EmailSignupRequest(BaseModel):
    email: EmailStr

    password: str = Field(
        min_length=8,
        max_length=128,
    )

    name: Optional[str] = Field(
        default=None,
        max_length=100,
    )

    timezone: Optional[str] = None


class EmailLoginRequest(BaseModel):
    email: EmailStr

    password: str = Field(
        min_length=1,
        max_length=128,
    )


class VerifyEmailRequest(BaseModel):
    token: str = Field(
        min_length=1,
    )


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str = Field(
        min_length=1,
    )

    password: str = Field(
        min_length=8,
        max_length=128,
    )