# app/config/plans.py

PLANS = {
    # ========================================================
    # GUEST
    # ========================================================

    "guest": {
        "limits": {
            "messages": {
                "daily": 10,
                "monthly": 100,
            },

            "flashcard_generations": {
                "daily": 2,
                "monthly": 10,
            },

            "quiz_generations": {
                "daily": 2,
                "monthly": 10,
            },

            "documents": 2,
            "chat_sessions": 5,
        },

        "rate_limit_per_minute": 5,

        "warning_threshold": 0.20,
    },

    # ========================================================
    # FREE
    # ========================================================

    "free": {
        "limits": {
            "messages": {
                "daily": 100,
                "monthly": 5000,
            },

            "flashcard_generations": {
                "daily": 10,
                "monthly": 200,
            },

            "quiz_generations": {
                "daily": 10,
                "monthly": 200,
            },

            "documents": 10,
            "chat_sessions": 50,
        },

        "rate_limit_per_minute": 10,

        "warning_threshold": 0.20,
    },

    # ========================================================
    # PRO
    # ========================================================

    "pro": {
        "limits": {
            "messages": {
                "daily": 1000,
                "monthly": 50000,
            },

            "flashcard_generations": {
                "daily": 100,
                "monthly": 3000,
            },

            "quiz_generations": {
                "daily": 100,
                "monthly": 3000,
            },

            "documents": 100,
            "chat_sessions": 500,
        },

        "rate_limit_per_minute": 30,

        "warning_threshold": 0.20,
    },
}