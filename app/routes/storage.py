# app/routes/dashboard.py

from fastapi import (
    APIRouter,
    Depends,
)

from app.db.mongo import db

from app.dependencies.auth import (
    get_current_identity
)

router = APIRouter()


@router.get("/")
def dashboard(
    current_user=Depends(
        get_current_user
    )
):

    user_id = str(
        current_user["_id"]
    )

    docs = list(
        db["documents"].find({
            "user_id": user_id
        })
    )

    flashcards = list(
        db["flashcards"].find({
            "user_id": user_id
        })
    )

    quizzes = list(
        db["quizzes"].find({
            "user_id": user_id
        })
    )

    progress = list(
        db["quiz_progress"].find({
            "user_id": user_id
        })
    )

    document_count = len(
        docs
    )

    flashcard_count = sum(
        len(f.get("data", []))
        for f in flashcards
    )

    quiz_count = sum(
        len(q.get("data", []))
        for q in quizzes
    )

    accuracy = 0

    if progress:

        scores = [
            p.get("score", 0)
            for p in progress
        ]

        accuracy = round(
            sum(scores)
            / len(scores),
            1
        )

    learning_progress = min(
        100,
        document_count * 15
        + flashcard_count // 2
        + quiz_count
    )

    return {
        "documents":
            document_count,
        "flashcards":
            flashcard_count,
        "quiz_questions":
            quiz_count,
        "accuracy":
            accuracy,
        "progress":
            learning_progress,
    }