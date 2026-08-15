# app/schemas/chat.py

from typing import Optional

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):

    question: str = Field(
        min_length=1,
        max_length=10000
    )

    chat_id: Optional[str] = None

    doc_id: Optional[str] = None

    start_page: Optional[int] = Field(
        default=None,
        ge=1
    )

    end_page: Optional[int] = Field(
        default=None,
        ge=1
    )

    focus_mode: Optional[str] = None