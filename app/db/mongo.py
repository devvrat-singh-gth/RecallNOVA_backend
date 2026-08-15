# app/db/mongo.py

from pymongo import MongoClient

from app.settings import MONGO_URI


client = MongoClient(
    MONGO_URI,
    serverSelectionTimeoutMS=5000,
)

db = client["ai_app"]


# ============================================================
# AUTH
# ============================================================

users = db["users"]

auth_sessions = db[
    "auth_sessions"
]

usage_tracking = db[
    "usage_tracking"
]

subscriptions = db[
    "subscriptions"
]


# ============================================================
# DOCUMENTS
# ============================================================

documents = db["documents"]


# ============================================================
# CHAT
# ============================================================

chat_sessions = db[
    "chat_sessions"
]


# ============================================================
# LEARNING
# ============================================================

flashcards = db[
    "flashcards"
]

quizzes = db[
    "quizzes"
]

quiz_progress = db[
    "quiz_progress"
]


# ============================================================
# INDEXES
# ============================================================

# -------------------------
# USERS
# -------------------------

users.create_index(
    "email",
    unique=True,
)

users.create_index(
    "google_id",
    unique=True,
    sparse=True,
)

# Email-auth tokens are stored as hashes.
# Sparse prevents documents without these fields
# from conflicting with each other.

users.create_index(
    "verification_token_hash",
    unique=True,
    sparse=True,
)

users.create_index(
    "password_reset_token_hash",
    unique=True,
    sparse=True,
)


# -------------------------
# DOCUMENTS
# -------------------------

documents.create_index(
    "user_id",
)


# -------------------------
# CHAT
# -------------------------

chat_sessions.create_index(
    [
        ("user_id", 1),
        ("updated_at", -1),
    ],
)

chat_sessions.create_index(
    [
        ("user_id", 1),
        ("chat_id", 1),
    ],
    unique=True,
)


# -------------------------
# LEARNING
# -------------------------

flashcards.create_index(
    [
        ("user_id", 1),
        ("doc_id", 1),
    ],
)

quizzes.create_index(
    [
        ("user_id", 1),
        ("doc_id", 1),
    ],
)

quiz_progress.create_index(
    [
        ("user_id", 1),
        ("doc_id", 1),
    ],
    unique=True,
)


# -------------------------
# USAGE
# -------------------------

usage_tracking.create_index(
    [
        ("user_id", 1),
        ("daily_period", 1),
        ("monthly_period", 1),
    ],
    unique=True,
)


# -------------------------
# AUTH SESSIONS
# -------------------------

auth_sessions.create_index(
    "session_id",
    unique=True,
)

auth_sessions.create_index(
    "token_hash",
    unique=True,
)

auth_sessions.create_index(
    [
        ("user_id", 1),
        ("revoked", 1),
    ],
)

auth_sessions.create_index(
    "expires_at",
    expireAfterSeconds=0,
)