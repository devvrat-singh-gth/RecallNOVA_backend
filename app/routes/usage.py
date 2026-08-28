from fastapi import APIRouter, Depends

from app.dependencies.auth import (
    get_current_identity,
)

from app.services.plan_service import (
    build_limit_warning,
    get_usage_limit_status,
)

router = APIRouter()


@router.get("/status")
def usage_status(
    current_user=Depends(
        get_current_identity
    )
):
    return {
        "messages": get_usage_limit_status(
            current_user,
            "messages"
        ),

        "flashcards": get_usage_limit_status(
            current_user,
            "flashcard_generations"
        ),

        "quizzes": get_usage_limit_status(
            current_user,
            "quiz_generations"
        ),
    }


@router.get("/warnings")
def usage_warnings(
    current_user=Depends(
        get_current_identity
    )
):
    return {
        "messages": build_limit_warning(
            current_user,
            "messages"
        ),

        "flashcards": build_limit_warning(
            current_user,
            "flashcard_generations"
        ),

        "quizzes": build_limit_warning(
            current_user,
            "quiz_generations"
        ),
    }