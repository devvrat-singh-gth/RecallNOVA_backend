from fastapi import APIRouter
from uuid import uuid4
from datetime import datetime
from bson import ObjectId

from app.db.mongo import (
    chat_sessions,
    documents
)

from app.schemas.chat import ChatRequest

from app.services.rag_service import (
    search_docs_by_id
)

from app.services.llm_service import ask_llm

from app.services.guard_service import (
    check_rate_limit,
    token_guard
)

from app.services.cache_service import (
    get_cached_response,
    save_cache
)

router = APIRouter()


# 🔥 CHAT TITLE
def generate_title(question: str, doc_id=None):

    title = question.strip()

    if len(title) > 45:
        title = title[:45] + "..."

    if doc_id:

        try:

            doc = documents.find_one({
                "_id": ObjectId(doc_id)
            })

            if doc and doc.get("name"):

                name = (
                    doc["name"]
                    .replace(".pdf", "")
                )

                return f"{name} • {title}"

        except:
            pass

    return title


# 🔥 CREATE CHAT / MESSAGE
@router.post("/")
def chat(req: ChatRequest):

    try:

        # 🔥 RATE LIMIT

        if not check_rate_limit(req.user_id):

            return {
                "error": "Too many requests"
            }

        # 🔥 CHAT ID

        chat_id = (
            req.chat_id
            or str(uuid4())
        )

        # 🔥 SANITIZE

        safe_q = token_guard(
            req.question
        )

        # 🔥 CACHE

        cached = get_cached_response(
            req.user_id,
            safe_q,
            req.doc_id,
            req.focus_mode
        )

        if cached:

            existing = (
                chat_sessions.find_one({
                    "chat_id": chat_id,
                    "user_id": req.user_id
                })
            )

            if not existing:

                chat_sessions.insert_one({

                    "chat_id": chat_id,

                    "user_id": req.user_id,

                    "title": generate_title(
                        req.question,
                        req.doc_id
                    ),

                    "created_at":
                    datetime.utcnow(),

                    "updated_at":
                    datetime.utcnow(),

                    "messages": []
                })

            return {
                "response": cached,
                "chat_id": chat_id,
                "cached": True
            }

        # 🔥 SEARCH DOCS

        context = search_docs_by_id(
            safe_q,
            req.user_id,
            req.doc_id,
            req.focus_mode
        )

        if not context:

            return {
                "response":
                "No relevant content found in selected documents.",
                "chat_id": chat_id
            }

        # 🔥 PROMPT

        prompt = f"""
You are RecallNova AI.

STRICT RULES:
- Answer ONLY using provided context
- Never hallucinate
- Return clean plain text
- No markdown
- No ** symbols
- No backticks
- Keep answers concise

CONTEXT:
{context}

QUESTION:
{safe_q}

FINAL ANSWER:
"""

        print(
            "PROMPT LENGTH:",
            len(prompt)
        )

        # 🔥 LLM

        response = ask_llm(prompt)

        print(
            "FINAL RESPONSE LENGTH:",
            len(response)
        )

        print(
            "RESPONSE PREVIEW:"
        )

        print(response[:500])

        # 🔥 SAVE CACHE

        save_cache(
            req.user_id,
            safe_q,
            response,
            req.doc_id,
            req.focus_mode
        )

        # 🔥 SAVE CHAT

        chat_sessions.update_one(

            {
                "chat_id": chat_id,
                "user_id": req.user_id
            },

            {

                "$setOnInsert": {

                    "title": generate_title(
                        req.question,
                        req.doc_id
                    ),

                    "created_at":
                    datetime.utcnow()
                },

                "$set": {

                    "updated_at":
                    datetime.utcnow()
                },

                "$push": {

                    "messages": {

                        "question":
                        req.question,

                        "response":
                        response,

                        "created_at":
                        datetime.utcnow()
                    }
                }
            },

            upsert=True
        )

        return {
            "response": response,
            "chat_id": chat_id
        }

    except Exception as e:

        print("CHAT ERROR:", e)

        return {
            "error": str(e)
        }


# 🔥 GET ALL CHATS
@router.get("/sessions")
def get_sessions(user_id: str):

    chats = list(

        chat_sessions.find(

            {
                "user_id": user_id
            },

            {
                "_id": 0,
                "chat_id": 1,
                "title": 1,
                "updated_at": 1
            }

        ).sort(
            "updated_at",
            -1
        )
    )

    return {
        "sessions": chats
    }


# 🔥 GET SINGLE CHAT
@router.get("/{chat_id}")
def get_chat(
    chat_id: str,
    user_id: str
):

    chat = chat_sessions.find_one(

        {
            "chat_id": chat_id,
            "user_id": user_id
        },

        {
            "_id": 0
        }
    )

    if not chat:

        return {
            "error": "Chat not found"
        }

    return chat


# 🔥 DELETE CHAT
@router.delete("/{chat_id}")
def delete_chat(
    chat_id: str,
    user_id: str
):

    chat_sessions.delete_one({

        "chat_id": chat_id,
        "user_id": user_id
    })

    return {
        "success": True
    }