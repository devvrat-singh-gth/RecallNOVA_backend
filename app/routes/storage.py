
# app/routes/storage.py

from fastapi import APIRouter, Depends

from app.db.mongo import documents
from app.dependencies.auth import get_current_identity

router = APIRouter()


@router.get("/")
def storage(
    current_user=Depends(get_current_identity)
):
    user_id = str(current_user["_id"])

    docs = list(
        documents.find(
            {"user_id": user_id},
            {
                "_id": 1,
                "name": 1,
                "size": 1,
                "created_at": 1,
            },
        ).sort("created_at", -1)
    )

    safe_documents = [
        {
            "id": str(doc["_id"]),
            "name": doc.get("name", "Untitled.pdf"),
            "size": int(doc.get("size", 0)),
            "created_at": doc.get("created_at"),
        }
        for doc in docs
    ]

    total_storage = sum(
        doc["size"] for doc in safe_documents
    )

    return {
        "total_docs": len(safe_documents),
        "storage_used": total_storage,
        "documents": safe_documents,
    }
