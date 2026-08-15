# app/config/plans.py

PLANS = {
    "free": {
        "limits": {
            "messages": {
                "daily": 100,
                "monthly": 1000,
            },

            "flashcard_generations": {
                "daily": 10,
                "monthly": 50,
            },

            "quiz_generations": {
                "daily": 10,
                "monthly": 50,
            },

            "documents": 10,
            "chat_sessions": 50,
        },

        "warning_threshold": 0.20,
    },

    "pro": {
        "limits": {
            "messages": {
                "daily": 1000,
                "monthly": 10000,
            },

            "flashcard_generations": {
                "daily": 100,
                "monthly": 1000,
            },

            "quiz_generations": {
                "daily": 100,
                "monthly": 1000,
            },

            "documents": 100,
            "chat_sessions": 500,
        },

        "warning_threshold": 0.20,
    },
}