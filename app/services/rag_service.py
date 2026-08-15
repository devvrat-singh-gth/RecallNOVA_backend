from fastapi import UploadFile
import fitz
from app.utils.hash_utils import generate_hash
from app.db.mongo import documents
from app.settings import MAX_PDF_MB
from bson import ObjectId



def extract_text_from_pdf(content):

    doc = fitz.open(
        stream=content,
        filetype="pdf"
    )

    full_text = ""

    pages = []

    for page_num, page in enumerate(doc):

        page_text = page.get_text()

        full_text += page_text + "\n"

        pages.append({
            "page": page_num + 1,
            "text": page_text
        })

    return {
        "text": full_text.strip(),
        "pages": pages,
        "total_pages": len(pages)
    }

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
    pdf_data = extract_text_from_pdf(content)

    if not pdf_data["text"]:
        return {
            "error":
            "Could not extract text from PDF"
        }

    filename = file.filename or "Untitled.pdf"   # 🔥 REAL FIX

    result = documents.insert_one({

        "user_id": user_id,

        "hash": doc_hash,

        "text": pdf_data["text"],

        "pages": pdf_data["pages"],

        "total_pages":
        pdf_data["total_pages"],

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
        pages = doc.get("pages")

        # NEW PDFs

        if pages:

            original_text = "\n".join(
                p.get("text", "")
                for p in pages
            )

        # OLD PDFs

        else:

            original_text = doc.get(
                "text",
                ""
            )

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
    start_page=None,
    end_page=None
):

    if doc_id:

        try:
            object_id = ObjectId(doc_id)
        except Exception:
            return ""

        docs = documents.find({
            "user_id": user_id,
            "_id": object_id
        })

    else:

        docs = documents.find({
            "user_id": user_id
        })

    query_words = query.lower().split()

    scored_chunks = []

    for doc in docs:

        pages = doc.get("pages", [])

        if pages:

            selected_pages = pages

            if (
                start_page is not None
                and end_page is not None
            ):
                selected_pages = [

                    p for p in pages

                    if start_page
                    <= p["page"]
                    <= end_page
                ]

            for page in selected_pages:

                text = page.get(
                    "text",
                    ""
                )

                lower = text.lower()

                score = 0

                for word in query_words:

                    if word in lower:
                        score += 3

                if query.lower() in lower:
                    score += 10

                if score > 0:

                    scored_chunks.append({
                        "score": score,
                        "chunk": text,
                        "page": page["page"]
                    })

        else:

            text = doc.get(
                "text",
                ""
            )

            lower = text.lower()

            score = 0

            for word in query_words:

                if word in lower:
                    score += 3

            if query.lower() in lower:
                score += 10

            if score > 0:

                scored_chunks.append({
                    "score": score,
                    "chunk": text
                })

    scored_chunks.sort(
        key=lambda x: x["score"],
        reverse=True
    )

    top_chunks = [
        x["chunk"]
        for x in scored_chunks[:5]
    ]

    return "\n\n".join(top_chunks)