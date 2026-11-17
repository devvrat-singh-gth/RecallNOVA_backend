
# app/routes/dashboard.py

import math

from fastapi import APIRouter, Depends

from app.db.mongo import db
from app.dependencies.auth import get_current_identity

router = APIRouter()


@router.get("/")
def dashboard(
    current_user=Depends(get_current_identity),
):
    user_id = str(current_user["_id"])

    documents = list(
        db["documents"].find(
            {"user_id": user_id},
            {"_id": 1, "name": 1},
        )
    )

    flashcards = list(
        db["flashcards"].find(
            {"user_id": user_id},
            {"doc_id": 1, "data": 1},
        )
    )

    quizzes = list(
        db["quizzes"].find(
            {"user_id": user_id},
            {"doc_id": 1, "data": 1},
        )
    )

    progress_records = list(
        db["quiz_progress"].find(
            {"user_id": user_id},
            {"doc_id": 1, "score": 1},
        )
    )

    document_stats = {}

    for document in documents:
        document_id = str(document["_id"])

        document_stats[document_id] = {
            "id": document_id,
            "name": document.get("name") or "Untitled document",
            "flashcards": 0,
            "quiz_questions": 0,
            "score": None,
        }

    flashcard_count = 0

    for item in flashcards:
        data = item.get("data")

        if not isinstance(data, list):
            continue

        count = len(data)
        flashcard_count += count

        document_id = str(item.get("doc_id", ""))

        if document_id in document_stats:
            document_stats[document_id]["flashcards"] += count

    quiz_question_count = 0

    for item in quizzes:
        data = item.get("data")

        if not isinstance(data, list):
            continue

        count = len(data)
        quiz_question_count += count

        document_id = str(item.get("doc_id", ""))

        if document_id in document_stats:
            document_stats[document_id]["quiz_questions"] += count

    scores = []

    for record in progress_records:
        score = record.get("score")

        if (
            not isinstance(score, (int, float))
            or isinstance(score, bool)
            or not math.isfinite(score)
            or not 0 <= score <= 100
        ):
            continue

        scores.append(float(score))

        document_id = str(record.get("doc_id", ""))

        if document_id in document_stats:
            document_stats[document_id]["score"] = round(
                float(score), 1
            )

    average_quiz_score = (
        round(sum(scores) / len(scores), 1)
        if scores
        else 0
    )

    document_breakdown = sorted(
        document_stats.values(),
        key=lambda item: item["name"].lower(),
    )

    return {
        "documents": len(documents),
        "flashcards": flashcard_count,
        "quiz_questions": quiz_question_count,
        "accuracy": average_quiz_score,
        "assessed_documents": len(scores),
        "document_breakdown": document_breakdown,
    }
