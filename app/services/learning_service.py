from app.services.llm_service import ask_llm
from app.db.mongo import db
from bson import ObjectId

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
                "data": parsed
            }
        },
        upsert=True
    )

    return parsed


# =========================
# ✅ QUIZ
# =========================
# =========================
# ✅ QUIZ
# =========================
def generate_quiz(
    user_id,
    count=5,
    topic="",
    difficulty="medium",
    doc_id=None,
    force_new=False
):

    # ✅ SAFE LIMIT
    count = min(max(count, 1), 10)

    if difficulty == "auto":
        difficulty = get_user_level(user_id, doc_id)

    existing_doc = quiz_collection.find_one({
        "user_id": user_id,
        "doc_id": doc_id,
        "topic": topic,
        "difficulty": difficulty
    })

    # ✅ START BUTTON
    if existing_doc and not force_new:
        return existing_doc.get("data", [])

    # ✅ GET CONTEXT
    context = get_doc_text(user_id, doc_id)

    if not context:
        return existing_doc.get("data", []) if existing_doc else []

    # ✅ SMALLER CONTEXT = BETTER JSON STABILITY
    context = context[:2000]

    topic_instruction = (
        f"Focus more on: {topic}"
        if topic else ""
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

    print("PROMPT LENGTH:", len(prompt))

    response = ask_llm(prompt)

    print("LLM RESPONSE:")
    print(response)
    import json
    import re

    valid = []

    print("REQUESTED COUNT:", count)
    print("RAW RESPONSE LENGTH:", len(response))

    try:

        # ✅ FIND FIRST [ AND LAST ]
        start = response.find("[")
        end = response.rfind("]")

        if start == -1 or end == -1:
            print("❌ NO JSON ARRAY FOUND")

            print("RAW RESPONSE:")
            print(response)

            return existing_doc.get("data", []) if existing_doc else []

        json_text = response[start:end + 1]

        print("JSON LENGTH:", len(json_text))

        parsed = json.loads(json_text)

        print("PARSED QUESTIONS:", len(parsed))

        valid = [
            q for q in parsed
            if isinstance(q, dict)
            and q.get("question")
            and isinstance(q.get("options"), list)
            and len(q["options"]) == 4
            and q.get("answer") in ["A", "B", "C", "D"]
        ]

        print("VALID QUESTIONS:", len(valid))

    except Exception as e:

        print("❌ PARSE ERROR:", e)

        print("RAW RESPONSE:")
        print(response)

        valid = []

        return existing_doc.get("data", []) if existing_doc else []

    # ✅ MERGE
    MAX_TOTAL = 100

    if existing_doc:

        current_data = existing_doc.get("data", [])

        existing_questions = set(
            q["question"]
            for q in current_data
            if "question" in q
        )

        filtered_new = [
            q for q in valid
            if q["question"] not in existing_questions
        ]

        new_data = current_data + filtered_new
        new_data = new_data[:MAX_TOTAL]

        quiz_collection.update_one(
            {"_id": existing_doc["_id"]},
            {"$set": {"data": new_data}}
        )

        return new_data

    # ✅ FIRST SAVE
    quiz_collection.update_one(
        {
            "user_id": user_id,
            "doc_id": doc_id,
            "topic": topic,
            "difficulty": difficulty
        },
        {
            "$set": {
                "data": valid,
                "count": count
            }
        },
        upsert=True
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