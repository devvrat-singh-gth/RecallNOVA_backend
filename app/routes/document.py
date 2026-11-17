# app/routes/document.py

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    UploadFile,
)

from bson import ObjectId
from bson.errors import InvalidId

from app.db.mongo import documents

from app.dependencies.auth import (
    get_current_identity,
)
from app.services.plan_service import (
    get_resource_limit,
)
from app.services.rag_service import (
    process_pdf
)
from app.settings import MAX_PDF_MB

router = APIRouter()


@router.get("/")
def get_docs(
current_user=Depends(
    get_current_identity
)
):

    user_id = str(
        current_user["_id"]
    )

    docs = documents.find({
        "user_id": user_id
    })

    return {
        "documents": [
            {
                "_id": str(d["_id"]),
                "name": d.get(
                    "name",
                    "Untitled.pdf"
                ),
                "size": d.get(
                    "size",
                    0
                ),
                "preview": d.get(
                    "text",
                    ""
                )[:100],
                "total_pages": d.get(
                    "total_pages",
                    1
                )
            }
            for d in docs
        ]
    }


@router.post("/upload")
async def upload(
    file: UploadFile = File(...),
    current_user=Depends(get_current_identity),
):
    user_id = str(current_user["_id"])

    document_limit = get_resource_limit(
        current_user,
        "documents",
    )

    document_count = documents.count_documents(
        {"user_id": user_id}
    )

    if document_count >= document_limit:
        raise HTTPException(
            status_code=429,
            detail={
                "code": "document_limit_reached",
                "message": "Document limit reached.",
            },
        )

    max_bytes = MAX_PDF_MB * 1024 * 1024

    # Read one byte beyond the limit so oversized files
    # can be rejected without loading the entire upload.
    content = await file.read(max_bytes + 1)

    if not content:
        raise HTTPException(
            status_code=400,
            detail="Uploaded PDF is empty.",
        )

    if len(content) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds the {MAX_PDF_MB} MB limit.",
        )

    # Check for a PDF header near the beginning of the file.
    if b"%PDF-" not in content[:1024]:
        raise HTTPException(
            status_code=400,
            detail="Uploaded file is not a valid PDF.",
        )

    result = process_pdf(
        file=file,
        content=content,
        user_id=user_id,
    )

    if result.get("error"):
        raise HTTPException(
            status_code=400,
            detail=result["error"],
        )

    return result


@router.delete("/{doc_id}")
def delete_doc(
    doc_id: str,
current_user=Depends(
    get_current_identity
)
):

    user_id = str(
        current_user["_id"]
    )

    try:
        obj_id = ObjectId(doc_id)

    except InvalidId:
        raise HTTPException(
            status_code=400,
            detail="Invalid document ID.",
        )

    result = documents.delete_one({
        "_id": obj_id,
        "user_id": user_id
    })

    if result.deleted_count == 0:
        raise HTTPException(
            status_code=404,
            detail="Document not found.",
        )

    return {
        "message":
            "Deleted successfully"
    }