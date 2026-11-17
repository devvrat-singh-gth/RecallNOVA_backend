# app/schemas/chat.py

from typing import Optional

from pydantic import BaseModel, Field, model_validator


class ChatRequest(BaseModel):

    question: str = Field(
        min_length=1,
        max_length=2000,
    )

    chat_id: Optional[str] = Field(
        default=None,
        max_length=100,
    )

    doc_id: Optional[str] = Field(
        default=None,
        max_length=100,
    )

    start_page: Optional[int] = Field(
        default=None,
        ge=1,
    )

    end_page: Optional[int] = Field(
        default=None,
        ge=1,
    )

    focus_mode: Optional[str] = Field(
        default=None,
        max_length=30,
    )

    @model_validator(mode="after")
    def validate_page_range(self):
        if (
            self.start_page is not None
            and self.end_page is not None
            and self.start_page > self.end_page
        ):
            raise ValueError(
                "start_page cannot be greater than end_page."
            )

        return self
