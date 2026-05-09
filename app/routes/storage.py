from fastapi import APIRouter
from app.db.mongo import documents

router = APIRouter()

@router.get("/")
def storage(user_id: str):
    docs = list(documents.find({"user_id": user_id}))
    total = sum([d.get("size", 1) for d in docs])

    return {
        "total_docs": len(docs),
        "storage_used": total,
        "documents": docs
    }
