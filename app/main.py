# app/main.py

import os

from fastapi import FastAPI

from fastapi.middleware.cors import (
    CORSMiddleware,
)

from app.routes import (
    auth,
    chat,
    document,
    learning,
    usage,
)

from app.routes.dashboard import (
    router as dashboard_router,
)


FRONTEND_URL = os.getenv(
    "FRONTEND_URL"
)

if not FRONTEND_URL:
    raise RuntimeError(
        "FRONTEND_URL is not configured"
    )


app = FastAPI(
    title="RecallNova AI Backend",
    version="1.0.0",
)


app.add_middleware(
    CORSMiddleware,

    allow_origins=[
        FRONTEND_URL.rstrip("/")
    ],

    allow_credentials=True,

    allow_methods=[
        "GET",
        "POST",
        "PUT",
        "PATCH",
        "DELETE",
        "OPTIONS",
    ],

    allow_headers=[
        "Authorization",
        "Content-Type",
    ],
)


app.include_router(
    auth.router,
    prefix="/auth",
    tags=["Auth"],
)

app.include_router(
    chat.router,
    prefix="/chat",
    tags=["Chat"],
)

app.include_router(
    document.router,
    prefix="/documents",
    tags=["Documents"],
)

app.include_router(
    learning.router,
    prefix="/learning",
    tags=["Learning"],
)

app.include_router(
    usage.router,
    prefix="/usage",
    tags=["Usage"],
)

app.include_router(
    dashboard_router,
    prefix="/dashboard",
    tags=["Dashboard"],
)


@app.get("/")
def home():
    return {
        "status":
            "Backend running",

        "service":
            "RecallNova AI",

        "version":
            "1.0",
    }


@app.on_event("startup")
def startup_event():
    print(
        "🚀 RecallNova backend started"
    )