# app/services/email_service.py

import os

import resend


RESEND_API_KEY = os.getenv(
    "RESEND_API_KEY"
)

RESEND_FROM_EMAIL = os.getenv(
    "RESEND_FROM_EMAIL"
)

RESEND_FROM_NAME = os.getenv(
    "RESEND_FROM_NAME",
    "RecallNova"
)


def _get_sender() -> str:
    if not RESEND_FROM_EMAIL:
        raise RuntimeError(
            "RESEND_FROM_EMAIL is not configured."
        )

    return (
        f"{RESEND_FROM_NAME} "
        f"<{RESEND_FROM_EMAIL}>"
    )


def _send_email(
    to_email: str,
    subject: str,
    html_content: str,
):
    if not RESEND_API_KEY:
        raise RuntimeError(
            "RESEND_API_KEY is not configured."
        )

    resend.api_key = RESEND_API_KEY

    try:
        result = resend.Emails.send(
            {
                "from": _get_sender(),
                "to": [to_email],
                "subject": subject,
                "html": html_content,
            }
        )

        return result

    except Exception as exc:
        print("RESEND ERROR:", repr(exc))
        raise RuntimeError(
            f"Unable to send email: {exc}"
        ) from exc


def send_verification_email(
    email: str,
    verification_url: str,
):
    return _send_email(
        email,
        "Verify your RecallNova email",
        f"""
        <div style="
            font-family:Arial,sans-serif;
            max-width:600px;
            margin:auto;
            padding:24px;
            color:#111;
        ">
            <h2>Welcome to RecallNova</h2>

            <p>
                Thanks for creating your RecallNova account.
                Please verify your email address to activate
                your account.
            </p>

            <p>
                <a
                    href="{verification_url}"
                    style="
                        display:inline-block;
                        padding:12px 18px;
                        background:#a3e635;
                        color:#000;
                        text-decoration:none;
                        border-radius:8px;
                        font-weight:bold;
                    "
                >
                    Verify Email
                </a>
            </p>

            <p>
                This link expires in 30 minutes.
            </p>

            <p style="color:#666;font-size:13px;">
                If you did not create this account,
                you can safely ignore this email.
            </p>
        </div>
        """,
    )


def send_password_reset_email(
    email: str,
    reset_url: str,
):
    return _send_email(
        email,
        "Reset your RecallNova password",
        f"""
        <div style="
            font-family:Arial,sans-serif;
            max-width:600px;
            margin:auto;
            padding:24px;
            color:#111;
        ">
            <h2>Reset your RecallNova password</h2>

            <p>
                We received a request to reset the password
                for your RecallNova account.
            </p>

            <p>
                <a
                    href="{reset_url}"
                    style="
                        display:inline-block;
                        padding:12px 18px;
                        background:#a3e635;
                        color:#000;
                        text-decoration:none;
                        border-radius:8px;
                        font-weight:bold;
                    "
                >
                    Reset Password
                </a>
            </p>

            <p>
                This link expires in 30 minutes.
            </p>

            <p style="color:#666;font-size:13px;">
                If you did not request this reset,
                you can safely ignore this email.
            </p>
        </div>
        """,
    )