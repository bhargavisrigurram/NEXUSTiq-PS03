"""Configuration management for NexusTiq24 PS03 Retail Copilot."""
import os
from pathlib import Path
from dotenv import load_dotenv

# Base directory
BASE_DIR = Path(__file__).resolve().parent.parent

# Load .env file
load_dotenv(dotenv_path=BASE_DIR / ".env")

# Directories
DATA_DIR = BASE_DIR / "data"
INDEX_DIR = BASE_DIR / "generated_index"
FRONTEND_DIR = BASE_DIR / "Frontend"

# Gemini API Configuration
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash-lite").strip()
EMBEDDING_MODEL = os.environ.get("EMBEDDING_MODEL", "gemini-embedding-001").strip()

# Server Configuration
HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", "8000"))

# Thresholds for Deterministic Retail Analytics
STOCKOUT_DAYS_THRESHOLD = 3.0       # Alert when stock covers less than 3 days
DEAD_STOCK_LOOKBACK_DAYS = 14       # Window to check for zero sales
SPIKE_RATIO_THRESHOLD = 1.5         # Recent 7d average >= 1.5x of 14d baseline (+50%+)
DROP_RATIO_THRESHOLD = 0.5          # Recent 7d average <= 0.5x of 14d baseline (-50%-)
TARGET_REORDER_DAYS_COVER = 7       # Standard default cover assumption for reorder advice

def is_gemini_configured() -> bool:
    """Check if a non-empty Gemini API key is configured."""
    return bool(GEMINI_API_KEY and len(GEMINI_API_KEY) > 5)

def get_masked_api_key() -> str:
    """Return a masked version of the API key for safe diagnostics."""
    if not is_gemini_configured():
        return "NOT_CONFIGURED"
    return f"{GEMINI_API_KEY[:4]}...{GEMINI_API_KEY[-4:]}"
