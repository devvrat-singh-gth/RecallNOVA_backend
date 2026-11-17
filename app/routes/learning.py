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
from bson import ObjectId
from bson.errors import InvalidId

from app.db.mongo import (
    db,
    documents,
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
    _valid_flashcards,
    _valid_quiz,
)

from app.services.plan_service import (
    ensure_usage_available,
)

from app.services.usage_service import (
    increment_usage,
)

from app.services.guard_service import (
    check_rate_limit,
)

router = APIRouter()


flashcards_collection = flashcards
quiz_collection = quizzes
progress_collection = quiz_progress
def validate_document_access(
    user_id: str,
    doc_id: str | None,
):
    """
    Validate that a supplied document belongs
    to the current user before using cached data
    or generating learning content.
    """

    if not doc_id:
        return

    try:
        object_id = ObjectId(doc_id)

    except (InvalidId, TypeError):
        raise HTTPException(
            status_code=404,
            detail="Document not found.",
        )

    document = documents.find_one({
        "_id": object_id,
        "user_id": user_id,
    })

    if not document:
        raise HTTPException(
            status_code=404,
            detail="Document not found.",
        )


def enforce_learning_rate_limit(
    current_user,
):
    user_id = str(
        current_user["_id"]
    )

    allowed = check_rate_limit(
        user_id,
        current_user.get(
            "plan",
            "free",
        ),
    )

    if not allowed:
        raise HTTPException(
            status_code=429,
            detail="Too many requests. Please try again shortly.",
        )

def require_registered_user(current_user):
    user_id = str(current_user.get("_id", ""))

    if (
        current_user.get("plan") == "guest"
        or user_id.startswith("guest_")
    ):
        raise HTTPException(
            status_code=403,
            detail="This feature is available to registered accounts only.",
        )


@router.get("/flashcards/check")
def check_flashcards(
    doc_id: str,
    current_user=Depends(get_current_identity),
):
    user_id = str(current_user["_id"])

    records = flashcards_collection.find({
        "user_id": user_id,
        "doc_id": doc_id,
    }).sort("count", -1)

    for record in records:
        data = record.get("data", [])
        count = record.get("count") or (
            len(data) if isinstance(data, list) else 0
        )

        if _valid_flashcards(data, count):
            return {
                "exists": True,
                "count": count,
            }

    return {
        "exists": False,
        "count": 0,
    }

@router.get("/quiz/check")
def check_quiz(
    doc_id: str,
    current_user=Depends(get_current_identity),
):
    require_registered_user(current_user)

    user_id = str(current_user["_id"])

    records = quiz_collection.find({
        "user_id": user_id,
        "doc_id": doc_id,
    }).sort("count", -1)

    for record in records:
        data = record.get("data", [])
        count = record.get("count") or (
            len(data) if isinstance(data, list) else 0
        )

        if _valid_quiz(data, count):
            return {
                "exists": True,
                "count": count,
            }

    return {
        "exists": False,
        "count": 0,
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

    enforce_learning_rate_limit(
        current_user
    )

    validate_document_access(
        user_id,
        doc_id,
    )   

    existing_records = flashcards_collection.find({
    "user_id": user_id,
    "doc_id": doc_id,
    "topic": topic,
    "difficulty": difficulty,
    "count": {"$gte": count},
    }).sort("count", 1)

    for existing in existing_records:
        stored_count = int(existing.get("count", 0))
        data = existing.get("data", [])

        if _valid_flashcards(data, stored_count):
            return {
                "flashcards": data[:count]
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

    if isinstance(result, dict) and result.get("error"):
        raise HTTPException(
            status_code=502,
            detail=result["error"],
        )

    if not isinstance(result, list) or not result:
        raise HTTPException(
            status_code=502,
            detail="Flashcard generation failed.",
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
        le=15,
    ),
    topic: str = Query(
        default="",
        max_length=200,
    ),
    difficulty: str = Query(
        default="medium",
    ),
    doc_id: str | None = None,
    force_new: bool = False,
    current_user=Depends(get_current_identity),
):
    require_registered_user(current_user)

    allowed_difficulties = {
        "easy",
        "medium",
        "hard",
        "auto",
    }

    if difficulty not in allowed_difficulties:
        raise HTTPException(
            status_code=400,
            detail="Invalid difficulty",
        )

    user_id = str(
        current_user["_id"]
    )

    enforce_learning_rate_limit(
        current_user
    )

    validate_document_access(
        user_id,
        doc_id,
    )    
        
    storage_difficulty = difficulty

    if difficulty == "auto":
        from app.services.learning_service import get_user_level

        storage_difficulty = get_user_level(
            user_id,
            doc_id,
        )

    # Reuse a valid existing set only when it matches
    # this user, document, topic, difficulty and count.
    if not force_new:
        existing_records = quiz_collection.find({
            "user_id": user_id,
            "doc_id": doc_id,
            "topic": topic,
            "difficulty": storage_difficulty,
            "count": {"$gte": count},
        }).sort("count", 1)

        for existing in existing_records:
            stored_count = int(existing.get("count", 0))
            data = existing.get("data", [])

            if _valid_quiz(data, stored_count):
                return {
                    "quiz": data[:count],
                }

    ensure_usage_available(
        current_user,
        "quiz_generations",
    )

    result = generate_quiz(
        user_id,
        count,
        topic,
        difficulty,
        doc_id,
        force_new,
    )

    if not isinstance(result, list) or not _valid_quiz(
        result,
        count,
    ):
        raise HTTPException(
            status_code=502,
            detail="Quiz generation failed.",
        )

    increment_usage(
        user_id,
        current_user.get("timezone", "UTC"),
        "quiz_generations",
    )

    return {
        "quiz": result,
    }


@router.post("/quiz/progress/save")
def save_progress(
    payload: dict,
    current_user=Depends(get_current_identity),
):
    user_id = str(current_user["_id"])
    require_registered_user(current_user)
    doc_id = payload.get("doc_id")

    if not isinstance(doc_id, str) or not doc_id.strip():
        raise HTTPException(
            status_code=400,
            detail="A valid doc_id is required.",
        )

    # Confirm that this document belongs to the
    # authenticated registered user or guest identity.
    try:
        object_id = ObjectId(doc_id)
    except (InvalidId, TypeError):
        raise HTTPException(
            status_code=400,
            detail="Invalid document ID.",
        )

    owned_document = documents.find_one(
        {
            "_id": object_id,
            "user_id": user_id,
        },
        {
            "_id": 1,
        },
    )

    if not owned_document:
        raise HTTPException(
            status_code=404,
            detail="Document not found.",
        )

    # Validate score when the frontend supplies it.
    score = payload.get("score")

    if score is not None:
        if (
            isinstance(score, bool)
            or not isinstance(score, (int, float))
            or not 0 <= score <= 100
        ):
            raise HTTPException(
                status_code=400,
                detail="Score must be a number between 0 and 100.",
            )

    # Do not allow clients to overwrite server-managed fields.
    safe_payload = {
        key: value
        for key, value in payload.items()
        if key not in {
            "_id",
            "user_id",
            "doc_id",
            "created_at",
            "updated_at",
            "guest_data",
        }
    }

    now = datetime.now(timezone.utc)

    safe_payload.update({
        "user_id": user_id,
        "doc_id": doc_id,
        "guest_data": user_id.startswith("guest_"),
        "updated_at": now,
    })

    progress_collection.update_one(
        {
            "user_id": user_id,
            "doc_id": doc_id,
        },
        {
            "$set": safe_payload,
            "$setOnInsert": {
                "created_at": now,
            },
        },
        upsert=True,
    )

    return {
        "status": "saved",
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
    require_registered_user(current_user)
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