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
current_user=Depends(
    get_current_identity
)
):

    user_id = str(
        current_user["_id"]
    )
    document_limit = get_resource_limit(
        current_user,
        "documents",
    )

    document_count = (
        documents.count_documents(
            {
                "user_id": user_id,
            }
        )
    )

    if document_count >= document_limit:
        raise HTTPException(
            status_code=429,
            detail={
                "code":
                    "document_limit_reached",

                "message":
                    "Document limit reached.",
            },
        )
    content = await file.read()

    print(
        "PDF SIZE:",
        len(content)
    )

    return process_pdf(
        file=file,
        content=content,
        user_id=user_id
    )


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

        return {
            "error":
                "Invalid document ID"
        }

    result = documents.delete_one({
        "_id": obj_id,
        "user_id": user_id
    })

    if result.deleted_count == 0:

        return {
            "error":
                "Not found or already deleted"
        }

    return {
        "message":
            "Deleted successfully"
    }