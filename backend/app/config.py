import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from the backend/ directory regardless of where the script is run from
_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=_env_path)

# Server Settings
PORT = int(os.getenv("PORT", 8000))
HOST = os.getenv("HOST", "0.0.0.0")

# LLM Config
# Supported: "openai", "gemini", "ollama", "anthropic", "openrouter"
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "").lower()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_API_KEYS = {}
_gemini_api_keys_str = os.getenv("GEMINI_API_KEYS", "")
if _gemini_api_keys_str:
    _keys_list = [k.strip() for k in _gemini_api_keys_str.split(",") if k.strip()]
    GEMINI_API_KEYS = {str(i + 1): key for i, key in enumerate(_keys_list)}
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")

# Default to "ollama" if no key is provided, or if explicitly requested
if not LLM_PROVIDER:
    if OPENROUTER_API_KEY:
        LLM_PROVIDER = "openrouter"
    elif OPENAI_API_KEY:
        LLM_PROVIDER = "openai"
    elif GEMINI_API_KEY or GEMINI_API_KEYS:
        LLM_PROVIDER = "gemini"
    elif ANTHROPIC_API_KEY:
        LLM_PROVIDER = "anthropic"
    else:
        LLM_PROVIDER = "ollama"

# Model names
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma3:12b")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "google/gemini-2.5-flash")
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
OPENROUTER_MAX_TOKENS = int(os.getenv("OPENROUTER_MAX_TOKENS", "4096"))

# Astrology Settings
DEFAULT_SIDEREAL = os.getenv("DEFAULT_SIDEREAL", "False").lower() in ("true", "1", "yes")
