# app/services/guest_service.py

import secrets


GUEST_ID_PREFIX = "guest_"


def create_guest_id() -> str:
    return (
        GUEST_ID_PREFIX
        + secrets.token_urlsafe(24)
    )