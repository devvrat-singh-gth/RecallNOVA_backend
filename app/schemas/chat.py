from pydantic import BaseModel
from typing import Optional


class ChatRequest(BaseModel):
    user_id: str
    question: str

    chat_id: Optional[str] = None
    doc_id: Optional[str] = None

    # 🔥 NEW
    focus_mode: Optional[str] = "balanced"

    # start | middle | end | balanced