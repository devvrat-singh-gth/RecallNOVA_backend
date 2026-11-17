
# app/services/learning_service.py

import json
import math
from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId

from app.db.mongo import db
from app.services.llm_service import ask_llm


flashcards_collection = db["flashcards"]
quiz_collection = db["quizzes"]

# Keep learning prompts comfortably below Groq's TPM limit.
LEARNING_CONTEXT_LIMIT = 2500


def _extract_json_array(response):
    """Extract a JSON array, including when the model adds code fences."""

    if not isinstance(response, str) or not response.strip():
        return None

    start = response.find("[")
    end = response.rfind("]")

    if start == -1 or end <= start:
        return None

    try:
        parsed = json.loads(response[start:end + 1])
    except (json.JSONDecodeError, TypeError):
        return None

    return parsed if isinstance(parsed, list) else None


def _valid_flashcards(data, expected_count):
    if not isinstance(data, list) or len(data) != expected_count:
        return False

    return all(
        isinstance(card, dict)
        and isinstance(card.get("question"), str)
        and bool(card["question"].strip())
        and isinstance(card.get("answer"), str)
        and bool(card["answer"].strip())
        for card in data
    )


def _valid_quiz(data, expected_count):
    if not isinstance(data, list) or len(data) != expected_count:
        return False

    for question in data:
        if not isinstance(question, dict):
            return False

        if not isinstance(question.get("question"), str):
            return False

        if not question["question"].strip():
            return False

        options = question.get("options")

        if (
            not isinstance(options, list)
            or len(options) != 4
            or not all(
                isinstance(option, str) and option.strip()
                for option in options
            )
        ):
            return False

        if question.get("answer") not in {"A", "B", "C", "D"}:
            return False

        if not isinstance(question.get("explanation"), str):
            return False

        if not question["explanation"].strip():
            return False

    return True


def get_doc_text(user_id, doc_id=None):
    """Retrieve bounded document content owned by this identity."""

    if doc_id:
        try:
            doc = db["documents"].find_one(
                {
                    "_id": ObjectId(doc_id),
                    "user_id": user_id,
                },
                {"text": 1},
            )
        except (InvalidId, TypeError):
            return ""

        text = doc.get("text", "") if doc else ""

        if not isinstance(text, str):
            return ""

        return text[:LEARNING_CONTEXT_LIMIT]

    docs = db["documents"].find(
        {"user_id": user_id},
        {"text": 1},
    )

    parts = []
    remaining = LEARNING_CONTEXT_LIMIT

    for doc in docs:
        text = doc.get("text", "")

        if not isinstance(text, str) or not text:
            continue

        part = text[:remaining]
        parts.append(part)
        remaining -= len(part)

        if remaining <= 0:
            break

    return "\n\n".join(parts)


def generate_flashcards(
    user_id,
    count=10,
    topic="",
    difficulty="medium",
    doc_id=None,
):
    existing = flashcards_collection.find_one(
        {
            "user_id": user_id,
            "doc_id": doc_id,
            "count": count,
            "topic": topic,
            "difficulty": difficulty,
        }
    )

    if existing and _valid_flashcards(
        existing.get("data"),
        count,
    ):
        return existing["data"]

    context = get_doc_text(user_id, doc_id)

    if not context.strip():
        return {"error": "No content found in the selected document."}

    topic_instruction = (
        f"Focus more on: {topic}"
        if topic
        else ""
    )

    prompt = f"""
Generate EXACTLY {count} high-quality flashcards.

Difficulty: {difficulty}

{topic_instruction}

Rules:
- Avoid repetition.
- Cover different concepts.
- Keep answers concise.
- Return ONLY a valid JSON array.
- Every item must contain string fields named question and answer.

Format:
[
  {{"question": "...", "answer": "..."}}
]

Content:
{context}
"""

    response = ask_llm(prompt)
    parsed = _extract_json_array(response)

    if not _valid_flashcards(parsed, count):
        return {
            "error": "Unable to generate a valid flashcard set. Please try again."
        }

    now = datetime.now(timezone.utc)

    flashcards_collection.update_one(
        {
            "user_id": user_id,
            "doc_id": doc_id,
            "count": count,
            "topic": topic,
            "difficulty": difficulty,
        },
        {
            "$set": {
                "data": parsed,
                "count": count,
                "topic": topic,
                "difficulty": difficulty,
                "created_at": now,
                "guest_data": user_id.startswith("guest_"),
            }
        },
        upsert=True,
    )

    return parsed


def generate_quiz(
    user_id,
    count=5,
    topic="",
    difficulty="medium",
    doc_id=None,
    force_new=False,
):
    count = min(max(int(count), 1), 15)

    if difficulty == "auto":
        difficulty = get_user_level(user_id, doc_id)

    query = {
        "user_id": user_id,
        "doc_id": doc_id,
        "topic": topic,
        "difficulty": difficulty,
        "count": count,
    }

    existing = quiz_collection.find_one(query)

    if (
        existing
        and not force_new
        and _valid_quiz(existing.get("data"), count)
    ):
        return existing["data"]

    context = get_doc_text(user_id, doc_id)

    if not context.strip():
        return []

    topic_instruction = (
        f"Focus more on: {topic}"
        if topic
        else ""
    )

    prompt = f"""
Generate EXACTLY {count} multiple-choice questions.

Difficulty: {difficulty}

{topic_instruction}

STRICT RULES:
- Return ONLY a valid JSON array.
- No markdown or explanations outside JSON.
- Every question must have exactly four non-empty options.
- answer must be exactly A, B, C, or D.
- Include a non-empty explanation.
- Return exactly {count} questions.

Format:
[
  {{
    "question": "...",
    "options": ["Option 1", "Option 2", "Option 3", "Option 4"],
    "answer": "A",
    "explanation": "..."
  }}
]

Content:
{context}
"""

    response = ask_llm(prompt)
    parsed = _extract_json_array(response)

    if not _valid_quiz(parsed, count):
        return []

    now = datetime.now(timezone.utc)

    quiz_collection.update_one(
        query,
        {
            "$set": {
                "data": parsed,
                "count": count,
                "created_at": now,
                "guest_data": user_id.startswith("guest_"),
            }
        },
        upsert=True,
    )

    return parsed


def get_user_level(user_id, doc_id):
    progress = db["quiz_progress"].find_one(
        {
            "user_id": user_id,
            "doc_id": doc_id,
        },
        {"score": 1},
    )

    if not progress:
        return "medium"

    score = progress.get("score", 0)

    if (
        isinstance(score, bool)
        or not isinstance(score, (int, float))
        or not math.isfinite(score)
    ):
        return "medium"

    if score >= 80:
        return "hard"

    if score <= 40:
        return "easy"

    return "medium"
