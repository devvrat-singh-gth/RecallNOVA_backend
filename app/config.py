import os
from dotenv import load_dotenv

# 🔥 FORCE CORRECT ROOT PATH
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
ENV_PATH = os.path.join(BASE_DIR, ".env")

load_dotenv(dotenv_path=ENV_PATH)

# 🔥 ENV VARIABLES
MONGO_URI = os.getenv("MONGO_URI")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_INDEX = os.getenv("PINECONE_INDEX")
HF_API_KEY = os.getenv("HF_API_KEY")
REDIS_URL = os.getenv("REDIS_URL")

# 🔥 HARD FAIL (DO NOT ALLOW SILENT FAILURE)
if not GROQ_API_KEY:
    raise ValueError("❌ GROQ_API_KEY missing")

if not PINECONE_API_KEY:
    raise ValueError("❌ PINECONE_API_KEY missing")

if not HF_API_KEY:
    raise ValueError("❌ HF_API_KEY missing")

MAX_DAILY_REQUESTS = 30
MAX_PDF_MB = 5