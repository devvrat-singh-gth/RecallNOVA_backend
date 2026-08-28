from app.services.llm_service import ask_llm
from app.db.mongo import db
from bson import ObjectId
from datetime import (
    datetime,
    timezone,
)
flashcards_collection = db["flashcards"]
quiz_collection = db["quizzes"]


# 🔥 GET DOC TEXT (FILTERED OR ALL)
def get_doc_text(user_id, doc_id=None):
    if doc_id:
        try:
            doc = db["documents"].find_one({
                "_id": ObjectId(doc_id),
                "user_id": user_id
            })

            text = doc.get("text", "") if doc else ""

            print("DOC ID:", doc_id)
            print("TEXT LENGTH:", len(text))

            return text

        except Exception as e:
            print("DOC FETCH ERROR:", e)
            return ""
    else:
        docs = db["documents"].find({"user_id": user_id})
        return "\n\n".join([d.get("text", "") for d in docs])

# =========================
# ✅ FLASHCARDS
# =========================
def generate_flashcards(user_id, count=10, topic="", difficulty="medium", doc_id=None):

    # 🔥 CACHE CHECK (PRODUCTION FIX)
    existing = flashcards_collection.find_one({
    "user_id": user_id,
    "doc_id": doc_id,
    "count": count,
    "topic": topic,
    "difficulty": difficulty
    })

    # ❌ DO NOT return if empty
    if existing and existing.get("data"):
         return existing["data"]

    # 🔥 CONTEXT
    context = get_doc_text(user_id, doc_id)

    if not context:
        return {"error": "No content found"}

    context = context[:4000]

    topic_instruction = f"Focus more on: {topic}" if topic else ""

    prompt = f"""
Generate {count} high-quality flashcards.

Difficulty: {difficulty}

{topic_instruction}

Rules:
- No repetition
- Cover different concepts
- Keep answers concise
- Return ONLY valid JSON

Format:
[
  {{"question": "...", "answer": "..."}}
]

Content:
{context}
"""

    response = ask_llm(prompt)

    try:
        import json
        parsed = json.loads(response)
    except:
        parsed = {"raw": response}

    # 🔥 SAVE
    flashcards_collection.update_one(
        {
            "user_id": user_id,
            "doc_id": doc_id,
            "count": count,
            "topic": topic,
            "difficulty": difficulty
        },
        {
            "$set": {

                "data": parsed,

                "count": count,

                "topic": topic,

                "difficulty": difficulty,

                "created_at": datetime.now(
                    timezone.utc
                ),

                "guest_data": user_id.startswith(
                    "guest_"
                )
            }
        },
        upsert=True
    )

    return parsed

# =========================
# ✅ QUIZ
# =========================
def generate_quiz(
    user_id,
    count=5,
    topic="",
    difficulty="medium",
    doc_id=None,
    force_new=False,
):
    count = min(
        max(
            int(count),
            1,
        ),
        10,
    )

    if difficulty == "auto":
        difficulty = get_user_level(
            user_id,
            doc_id,
        )

    existing_doc = (
        quiz_collection.find_one(
            {
                "user_id": user_id,

                "doc_id": doc_id,

                "topic": topic,

                "difficulty":
                    difficulty,

                "count": count,
            }
        )
    )

    if (
        existing_doc
        and existing_doc.get("data")
        and not force_new
    ):
        return existing_doc["data"]

    context = get_doc_text(
        user_id,
        doc_id,
    )

    if not context:
        return []

    context = context[:2000]

    topic_instruction = (
        f"Focus more on: {topic}"
        if topic
        else ""
    )

    prompt = f"""
Generate EXACTLY {count} multiple choice questions.

Difficulty: {difficulty}

{topic_instruction}

STRICT RULES:
- Return ONLY VALID JSON
- No markdown
- No explanations outside JSON
- Exactly 4 options
- answer must ONLY be A/B/C/D
- Include explanation
- Output COMPLETE JSON ARRAY
- No trailing commas

Format:
[
  {{
    "question": "...",
    "options": ["A", "B", "C", "D"],
    "answer": "A",
    "explanation": "..."
  }}
]

Content:
{context}
"""

    response = ask_llm(
        prompt
    )

    import json

    try:
        start = response.find("[")
        end = response.rfind("]")

        if start == -1 or end == -1:
            return []

        parsed = json.loads(
            response[
                start:end + 1
            ]
        )

        valid = [
            question
            for question in parsed
            if (
                isinstance(
                    question,
                    dict,
                )
                and question.get(
                    "question"
                )
                and isinstance(
                    question.get(
                        "options"
                    ),
                    list,
                )
                and len(
                    question[
                        "options"
                    ]
                ) == 4
                and question.get(
                    "answer"
                ) in {
                    "A",
                    "B",
                    "C",
                    "D",
                }
            )
        ]

    except Exception:
        return []

    if not valid:
        return []

    valid = valid[:count]

    quiz_collection.update_one(
        {
            "user_id": user_id,

            "doc_id": doc_id,

            "topic": topic,

            "difficulty":
                difficulty,

            "count": count,
        },
        {
            "$set": {

                "data": valid,

                "count": count,

                "created_at": datetime.now(
                    timezone.utc
                ),

                "guest_data": user_id.startswith(
                    "guest_"
                )
            },
        },
        upsert=True,
    )

    return valid

def get_user_level(user_id, doc_id):
    p = db["quiz_progress"].find_one({
        "user_id": user_id,
        "doc_id": doc_id
    })

    if not p:
        return "medium"

    score = p.get("score", 0)

    if score >= 80:
        return "hard"
    elif score <= 40:
        return "easy"
    return "medium"