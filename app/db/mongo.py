from pymongo import MongoClient
from app.config import MONGO_URI

client = MongoClient(MONGO_URI)

db = client["ai_app"]

# USERS
users = db["users"]

# DOCUMENTS (add doc_id later automatically via _id)
documents = db["documents"]

# CHAT SESSIONS (NEW)
chat_sessions = db["chat_sessions"]
chat_sessions.create_index("chat_id")
chat_sessions.create_index("user_id")

documents.create_index("user_id")
# LEARNING
flashcards = db["flashcards"]
quizzes = db["quizzes"]