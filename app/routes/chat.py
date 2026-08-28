# app/routes/chat.py

from datetime import datetime, timezone
from uuid import uuid4

from bson import ObjectId
from bson.errors import InvalidId

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)

from app.db.mongo import (
    chat_sessions,
    documents,
)

from app.dependencies.auth import (
    get_current_identity,
)

from app.schemas.chat import (
    ChatRequest
)

from app.services.rag_service import (
    search_docs_by_id
)

from app.services.llm_service import (
    ask_llm
)

from app.services.guard_service import (
    check_rate_limit,
    token_guard
)

from app.services.cache_service import (
    get_cached_response,
    save_cache
)

from app.services.plan_service import (
    ensure_usage_available,
    get_resource_limit,
)

from app.services.usage_service import (
    increment_usage
)


router = APIRouter()


def generate_title(
    question: str,
    doc_id=None
):

    title = question.strip()

    if len(title) > 45:
        title = title[:45] + "..."

    if doc_id:

        try:
            doc = documents.find_one({
                "_id": ObjectId(doc_id),
                "user_id": user_id
            })

            if doc and doc.get("name"):

                name = doc["name"]

                if name.lower().endswith(".pdf"):
                    name = name[:-4]

                return (
                    f"{name} • {title}"
                )

        except (
            InvalidId,
            TypeError
        ):
            pass

    return title


@router.post("/")
def chat(
    req: ChatRequest,
current_user=Depends(
    get_current_identity
)
):

    user_id = str(
        current_user["_id"]
    )

    if not check_rate_limit(
        user_id,
        current_user.get(
            "plan",
            "free",
        ),
    ):
        raise HTTPException(
            status_code=429,
            detail="Too many requests"
        )

    ensure_usage_available(
        current_user,
        "messages"
    )
    chat_id = (
        req.chat_id
        or str(uuid4())
    )
    existing_chat = chat_sessions.find_one(
        {
            "chat_id": chat_id,
            "user_id": user_id,
        },
        {
            "_id": 1,
        },
    )

    if (
        not existing_chat
        and not req.chat_id
    ):
        chat_limit = get_resource_limit(
            current_user,
            "chat_sessions",
        )

        current_chat_count = (
            chat_sessions.count_documents(
                {
                    "user_id": user_id,
                }
            )
        )

        if current_chat_count >= chat_limit:
            raise HTTPException(
                status_code=429,
                detail={
                    "code":
                        "chat_session_limit_reached",

                    "message":
                        "Chat session limit reached.",
                },
            )
    safe_q = token_guard(
        req.question
    )
    cached = get_cached_response(
        user_id,
        safe_q,
        req.doc_id or "",
        req.focus_mode or "balanced"
    )

    if cached:

        existing = chat_sessions.find_one({
            "chat_id": chat_id,
            "user_id": user_id
        })

        now = datetime.now(
            timezone.utc
        )

        if not existing:

            chat_sessions.insert_one({

                "chat_id": chat_id,

                "user_id": user_id,

                "title": generate_title(
                    req.question,
                    req.doc_id
                ),

                "created_at": now,

                "updated_at": now,

                "guest_data": user_id.startswith(
                    "guest_"
                ),

                "messages": []
            })

        return {
            "response": cached,
            "chat_id": chat_id,
            "cached": True
        }

    context = search_docs_by_id(
        query=safe_q,
        user_id=user_id,
        doc_id=req.doc_id,
        start_page=req.start_page,
        end_page=req.end_page
    )

    if not context:

        return {
            "response":
                "No relevant content found "
                "in selected documents.",
            "chat_id": chat_id
        }

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

    response = ask_llm(
        prompt
    )

    if not response:
        raise HTTPException(
            status_code=503,
            detail="AI service unavailable"
        )

    save_cache(
        user_id,
        safe_q,
        response,
        req.doc_id or "",
        req.focus_mode or "balanced"
    )

    now = datetime.now(
        timezone.utc
    )

    chat_sessions.update_one(

        {
            "chat_id": chat_id,
            "user_id": user_id
        },

        {
            "$setOnInsert": {

                "title": generate_title(
                    req.question,
                    req.doc_id
                ),

                "created_at": now,

                "guest_data": user_id.startswith(
                    "guest_"
                ),
            },

            "$set": {
                "updated_at": now,
                "selected_doc": req.doc_id,
                "start_page": req.start_page,
                "end_page": req.end_page,
            },

            "$push": {
                "messages": {
                    "question":
                        req.question,
                    "response":
                        response,
                    "created_at":
                        now,
                }
            }
        },

        upsert=True
    )
    increment_usage(
        user_id,
        current_user.get(
            "timezone",
            "UTC"
        ),
        "messages"
    )

    return {
        "response": response,
        "chat_id": chat_id
    }


@router.get("/sessions")
def get_sessions(
current_user=Depends(
    get_current_identity
)
):

    user_id = str(
        current_user["_id"]
    )

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


@router.get("/{chat_id}")
def get_chat(
    chat_id: str,
current_user=Depends(
    get_current_identity
)
):

    user_id = str(
        current_user["_id"]
    )

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

        raise HTTPException(
            status_code=404,
            detail="Chat not found"
        )

    return chat


@router.delete("/{chat_id}")
def delete_chat(
    chat_id: str,
current_user=Depends(
    get_current_identity
)
):

    user_id = str(
        current_user["_id"]
    )

    result = chat_sessions.delete_one({
        "chat_id": chat_id,
        "user_id": user_id
    })

    return {
        "success": True,
        "deleted": result.deleted_count > 0
    }