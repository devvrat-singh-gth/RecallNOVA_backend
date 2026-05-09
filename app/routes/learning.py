from fastapi import APIRouter
from app.services.learning_service import (
    generate_flashcards,
    generate_quiz
)
from app.db.mongo import db

router = APIRouter()


flashcards_collection = db["flashcards"]
quiz_collection = db["quizzes"]
progress_collection = db["quiz_progress"]

@router.get("/flashcards/check")
def check_flashcards(user_id: str, doc_id: str):

    doc = flashcards_collection.find_one({
        "user_id": user_id,
        "doc_id": doc_id
    })

    has_data = (
        doc and
        doc.get("data") and
        len(doc.get("data")) > 0
    )

    return {
        "exists": bool(has_data),

        "count": len(
            doc.get("data", [])
        ) if doc else 0
    }
@router.get("/quiz/check")
def check_quiz(user_id: str, doc_id: str):
    doc = quiz_collection.find_one({
        "user_id": user_id,
        "doc_id": doc_id
    })

    has_data = doc and doc.get("data") and len(doc.get("data")) > 0

    return {
        "exists": bool(has_data),
        "count": len(doc.get("data", [])) if doc else 0
    }
@router.get("/flashcards")
def flashcards(
    user_id: str,
    count: int = 10,
    topic: str = "",
    difficulty: str = "medium",
    doc_id: str = None
):
    return {
        "flashcards": generate_flashcards(user_id, count, topic, difficulty, doc_id)
    }


@router.get("/quiz")
def quiz(
    user_id: str,
    count: int = 5,
    topic: str = "",
    difficulty: str = "medium",
    doc_id: str = None,
    force_new: bool = False
):
    return {
"quiz": generate_quiz(user_id, count, topic, difficulty, doc_id, force_new)    }

@router.post("/quiz/progress/save")
def save_progress(payload: dict):
    progress_collection.update_one(
        {
            "user_id": payload["user_id"],
            "doc_id": payload["doc_id"]
        },
        {
            "$set": payload
        },
        upsert=True
    )
    return {"status": "saved"}
@router.get("/quiz/progress")
def get_progress(user_id: str, doc_id: str):
    data = progress_collection.find_one({
        "user_id": user_id,
        "doc_id": doc_id
    })

    if data:
        data["_id"] = str(data["_id"])

    return {"progress": data}