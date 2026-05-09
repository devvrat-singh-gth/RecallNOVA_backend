from fastapi import UploadFile
import fitz
from app.utils.hash_utils import generate_hash
from app.db.mongo import documents
from app.config import MAX_PDF_MB
from bson import ObjectId



def extract_text_from_pdf(content):
    doc = fitz.open(stream=content, filetype="pdf")
    text = ""

    for page in doc:
        text += page.get_text()

    return text.strip()


def process_pdf(file: UploadFile, user_id):
    content = file.file.read()   # 🔥 FIX

    if len(content) > MAX_PDF_MB * 1024 * 1024:
        return {"error": "File too large"}

    doc_hash = generate_hash(content)

    existing = documents.find_one({
        "hash": doc_hash,
        "user_id": user_id
    })

    if existing:
        return {"message": "Already uploaded"}

    text = extract_text_from_pdf(content)

    if not text:
        return {"error": "Could not extract text from PDF"}

    filename = file.filename or "Untitled.pdf"   # 🔥 REAL FIX

    result = documents.insert_one({
        "user_id": user_id,
        "hash": doc_hash,
        "text": text,
        "name": filename,
        "size": len(content)
    })

    return {
        "message": "Stored successfully",
        "doc_id": str(result.inserted_id)
    }

def search_docs(query, user_id):
    docs = documents.find({"user_id": user_id})

    query_words = query.lower().split()
    scored_chunks = []

    for doc in docs:
        original_text = doc.get("text", "")
        text_lower = original_text.lower()

        # 🔥 chunking (keep original + lower)
        chunks = [
            (original_text[i:i+1000], text_lower[i:i+1000])
            for i in range(0, len(original_text), 1000)
        ]

        for original_chunk, chunk_lower in chunks:
            score = 0

            for word in query_words:
                if word in chunk_lower:
                    score += 2  # 🔥 boost match

            # 🔥 slight boost for longer meaningful chunks
            if len(original_chunk) > 200:
                score += 1

            if score > 1:  # 🔥 ignore weak matches
                scored_chunks.append((score, original_chunk))

    # 🔥 sort by relevance
    scored_chunks.sort(reverse=True, key=lambda x: x[0])

    # 🔥 take best chunks
    top_chunks = [chunk for _, chunk in scored_chunks[:5]]

    return "\n\n".join(top_chunks)
def search_docs_by_id(
    query,
    user_id,
    doc_id=None,
    focus_mode="balanced"
):

    if doc_id:

        docs = documents.find({
            "user_id": user_id,
            "_id": ObjectId(doc_id)
        })

    else:

        docs = documents.find({
            "user_id": user_id
        })

    query_words = query.lower().split()

    scored_chunks = []

    for doc in docs:

        original_text = doc.get("text", "")
        text_lower = original_text.lower()

        # 🔥 SMARTER CHUNK SIZE
        chunk_size = 700
        overlap = 120

        chunks = []

        for i in range(
            0,
            len(original_text),
            chunk_size - overlap
        ):

            original_chunk = original_text[
                i:i + chunk_size
            ]

            lower_chunk = text_lower[
                i:i + chunk_size
            ]

            chunks.append((
                i,
                original_chunk,
                lower_chunk
            ))

        total_chunks = len(chunks)

        for idx, (
            position,
            original_chunk,
            chunk_lower
        ) in enumerate(chunks):

            score = 0

            # 🔥 QUERY MATCHING
            for word in query_words:

                if word in chunk_lower:
                    score += 3

            # 🔥 PHRASE BOOST
            if query.lower() in chunk_lower:
                score += 10

            # 🔥 CONTENT BOOST
            if len(original_chunk) > 300:
                score += 1

            # 🔥 FOCUS MODE BOOST
            if focus_mode == "start":
                score += max(
                    0,
                    20 - idx
                )

            elif focus_mode == "middle":

                middle = total_chunks / 2

                score += max(
                    0,
                    20 - abs(idx - middle)
                )

            elif focus_mode == "end":

                score += idx

            if score > 2:

                scored_chunks.append({
                    "score": score,
                    "chunk": original_chunk
                })

    scored_chunks.sort(
        key=lambda x: x["score"],
        reverse=True
    )

    top_chunks = [
        c["chunk"]
        for c in scored_chunks[:4]
    ]

    return "\n\n".join(top_chunks)