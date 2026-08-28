# app/routes/learning.py

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
)
from datetime import (
    datetime,
    timezone,
)
from app.db.mongo import (
    db,
    flashcards,
    quizzes,
    quiz_progress,
)

from app.dependencies.auth import (
    get_current_identity,
)

from app.services.learning_service import (
    generate_flashcards,
    generate_quiz,
)

from app.services.plan_service import (
    ensure_usage_available,
)

from app.services.usage_service import (
    increment_usage,
)


router = APIRouter()


flashcards_collection = flashcards
quiz_collection = quizzes
progress_collection = quiz_progress


@router.get("/flashcards/check")
def check_flashcards(
    doc_id: str,
current_user=Depends(
    get_current_identity
)
):

    user_id = str(
        current_user["_id"]
    )

    doc = flashcards_collection.find_one({
        "user_id": user_id,
        "doc_id": doc_id
    })

    data = (
        doc.get("data", [])
        if doc
        else []
    )

    return {
        "exists": bool(data),
        "count": len(data)
    }


@router.get("/quiz/check")
def check_quiz(
    doc_id: str,
current_user=Depends(
    get_current_identity
)
):

    user_id = str(
        current_user["_id"]
    )

    doc = quiz_collection.find_one({
        "user_id": user_id,
        "doc_id": doc_id
    })

    data = (
        doc.get("data", [])
        if doc
        else []
    )

    return {
        "exists": bool(data),
        "count": len(data)
    }


@router.get("/flashcards")
def flashcards_route(
    count: int = Query(
        default=10,
        ge=1,
        le=20
    ),
    topic: str = Query(
        default="",
        max_length=200
    ),
    difficulty: str = Query(
        default="medium"
    ),
    doc_id: str | None = None,
current_user=Depends(
    get_current_identity
)
):

    allowed_difficulties = {
        "easy",
        "medium",
        "hard",
    }

    if difficulty not in allowed_difficulties:
        raise HTTPException(
            status_code=400,
            detail="Invalid difficulty"
        )

    user_id = str(
        current_user["_id"]
    )

    existing = flashcards_collection.find_one({
        "user_id": user_id,
        "doc_id": doc_id,
        "count": count,
        "topic": topic,
        "difficulty": difficulty,
    })

    if existing and existing.get(
        "data"
    ):
        return {
            "flashcards":
                existing["data"]
        }

    ensure_usage_available(
        current_user,
        "flashcard_generations"
    )

    result = generate_flashcards(
        user_id,
        count,
        topic,
        difficulty,
        doc_id
    )

    if isinstance(result, dict) and result.get(
        "error"
    ):
        raise HTTPException(
            status_code=400,
            detail=result["error"]
        )

    increment_usage(
        user_id,
        current_user.get(
            "timezone",
            "UTC"
        ),
        "flashcard_generations"
    )

    return {
        "flashcards": result
    }


@router.get("/quiz")
def quiz_route(
    count: int = Query(
        default=5,
        ge=1,
        le=10
    ),
    topic: str = Query(
        default="",
        max_length=200
    ),
    difficulty: str = Query(
        default="medium"
    ),
    doc_id: str | None = None,
    force_new: bool = False,
current_user=Depends(
    get_current_identity
)
):

    allowed_difficulties = {
        "easy",
        "medium",
        "hard",
        "auto",
    }

    if difficulty not in allowed_difficulties:
        raise HTTPException(
            status_code=400,
            detail="Invalid difficulty"
        )

    user_id = str(
        current_user["_id"]
    )
    storage_difficulty = difficulty

    if difficulty == "auto":
        from app.services.learning_service import (
            get_user_level,
        )

        storage_difficulty = get_user_level(
            user_id,
            doc_id,
        )

    existing = quiz_collection.find_one(
        {
            "user_id": user_id,
            "doc_id": doc_id,
            "topic": topic,
            "difficulty": storage_difficulty,
            "count": count,
        }
    )

    if existing and not force_new:
        data = existing.get(
            "data",
            []
        )

        if data:
            return {
                "quiz": data
            }

    ensure_usage_available(
        current_user,
        "quiz_generations"
    )

    result = generate_quiz(
        user_id,
        count,
        topic,
        difficulty,
        doc_id,
        force_new
    )

    if not isinstance(result, list):
        raise HTTPException(
            status_code=500,
            detail="Quiz generation failed"
        )

    increment_usage(
        user_id,
        current_user.get(
            "timezone",
            "UTC"
        ),
        "quiz_generations"
    )

    return {
        "quiz": result
    }


@router.post("/quiz/progress/save")
def save_progress(
    payload: dict,
current_user=Depends(
    get_current_identity
)
):

    user_id = str(
        current_user["_id"]
    )

    doc_id = payload.get(
        "doc_id"
    )

    if not doc_id:
        raise HTTPException(
            status_code=400,
            detail="doc_id is required"
        )

    safe_payload = {
        key: value
        for key, value in payload.items()
        if key not in {
            "_id",
            "user_id"
        }
    }

    safe_payload["user_id"] = user_id
    safe_payload["doc_id"] = doc_id
    safe_payload["guest_data"] = (
        user_id.startswith(
            "guest_"
        )
    )
    safe_payload["created_at"] = (
    datetime.now(
        timezone.utc
        )
    )
        
    progress_collection.update_one(
        {
            "user_id": user_id,
            "doc_id": doc_id
        },
        {
            "$set": safe_payload
        },
        upsert=True
    )

    return {
        "status": "saved"
    }


@router.get("/quiz/progress")
def get_progress(
    doc_id: str,
current_user=Depends(
    get_current_identity
)
):

    user_id = str(
        current_user["_id"]
    )

    data = progress_collection.find_one({
        "user_id": user_id,
        "doc_id": doc_id
    })

    if data:
        data["_id"] = str(
            data["_id"]
        )

    return {
        "progress": data
    }