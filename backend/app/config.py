import os
from dotenv import load_dotenv

load_dotenv()

# --- API Keys ---
# Paste your Groq API key directly below, OR set it as an environment variable
# Get a free key at https://console.groq.com
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "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")
LLM_MODEL = os.getenv("LLM_MODEL", "llama-3.3-70b-versatile")

# --- Database ---
DATABASE_PATH = os.getenv("DATABASE_PATH", "data/onboarding.db")
CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", "data/chroma_db")

# --- Embedding Model ---
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")

# --- Skill Gap Thresholds ---
MASTERY_THRESHOLD = 0.85  # BKT mastery probability threshold
GAP_SIGNIFICANCE_THRESHOLD = 15  # Minimum gap score (0-100) to flag
TOP_K_COURSES = 5  # Number of courses to retrieve per skill gap

# --- O*NET Standardization ---
ONET_IMPORTANCE_MIN = 1
ONET_IMPORTANCE_MAX = 5
ONET_LEVEL_MIN = 0
ONET_LEVEL_MAX = 7
