from fastapi import APIRouter, UploadFile, File
from app.services.rag_service import process_pdf
from app.db.mongo import documents
from bson import ObjectId
from bson.errors import InvalidId

router = APIRouter()
@router.get("/")
def get_docs(user_id: str):
    docs = documents.find({"user_id": user_id})

    return {
        "documents": [
           {
  "_id": str(d["_id"]),
  "name": d.get("name", "Untitled.pdf"),
  "size": d.get("size", 0),
  "preview": d.get("text", "")[:100]
}
            for d in docs
        ]
    }
@router.post("/upload")
async def upload(file: UploadFile = File(...), user_id: str = ""):
    return process_pdf(file, user_id)
@router.delete("/{doc_id}")
def delete_doc(doc_id: str, user_id: str):
    try:
        obj_id = ObjectId(doc_id)
    except InvalidId:
        return {"error": "Invalid document ID"}

    result = documents.delete_one({
        "_id": obj_id,
        "user_id": user_id
    })

    if result.deleted_count == 0:
        return {"error": "Not found or already deleted"}

    return {"message": "Deleted successfully"}