# 🔥 FORCE LOAD ENV FROM ROOT
from dotenv import load_dotenv

import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
ENV_PATH = os.path.join(BASE_DIR, ".env")
# 🔥 IMPORTS AFTER ENV
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes import chat, document, storage, learning

# 🔥 INIT APP
app = FastAPI(
    title="RecallNova AI Backend",
    version="1.0.0"
)

# 🔥 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 🔥 ROUTES
app.include_router(chat.router, prefix="/chat", tags=["Chat"])
app.include_router(document.router, prefix="/documents", tags=["Documents"])
app.include_router(storage.router, prefix="/storage", tags=["Storage"])
app.include_router(learning.router, prefix="/learning", tags=["Learning"])
# 🔥 HEALTH CHECK
@app.get("/")
def home():
    return {
        "status": "Backend running",
        "service": "RecallNova AI",
        "version": "1.0"
    }

# 🔥 DEBUG (IMPORTANT — REMOVE LATER)
@app.on_event("startup")
def startup_event():
    print("🚀 Backend Started Successfully")