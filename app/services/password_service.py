# app/services/password_service.py

import base64
import hashlib
import hmac
import os
import secrets


SALT_BYTES = 16
HASH_BYTES = 32

SCRYPT_N = int(
    os.getenv(
        "PASSWORD_SCRYPT_N",
        "16384",
    )
)

SCRYPT_R = int(
    os.getenv(
        "PASSWORD_SCRYPT_R",
        "8",
    )
)

SCRYPT_P = int(
    os.getenv(
        "PASSWORD_SCRYPT_P",
        "1",
    )
)


def hash_password(password: str) -> str:
    if not password or len(password) < 8:
        raise ValueError(
            "Password must contain at least 8 characters."
        )

    salt = secrets.token_bytes(SALT_BYTES)

    derived = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=SCRYPT_N,
        r=SCRYPT_R,
        p=SCRYPT_P,
        dklen=HASH_BYTES,
    )

    return (
        f"scrypt${SCRYPT_N}${SCRYPT_R}${SCRYPT_P}$"
        f"{base64.urlsafe_b64encode(salt).decode()}$"
        f"{base64.urlsafe_b64encode(derived).decode()}"
    )


def verify_password(
    password: str,
    stored_hash: str,
) -> bool:
    try:
        (
            algorithm,
            n,
            r,
            p,
            salt_b64,
            hash_b64,
        ) = stored_hash.split("$")

        if algorithm != "scrypt":
            return False

        salt = base64.urlsafe_b64decode(
            salt_b64.encode()
        )

        expected = base64.urlsafe_b64decode(
            hash_b64.encode()
        )

        actual = hashlib.scrypt(
            password.encode("utf-8"),
            salt=salt,
            n=int(n),
            r=int(r),
            p=int(p),
            dklen=len(expected),
        )

        return hmac.compare_digest(
            actual,
            expected,
        )

    except (
        ValueError,
        TypeError,
        UnicodeDecodeError,
    ):
        return False