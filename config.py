import os

# Server
PORT = 3015
HOST = "0.0.0.0"

# Directories
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOWNLOADS_DIR = os.path.join(BASE_DIR, "downloads")
TRANSCRIPTS_DIR = os.path.join(BASE_DIR, "transcripts")

# LLM — DeepSeek
DEEPSEEK_API_KEY = os.environ.get(
    "DEEPSEEK_API_KEY",
    "your-deepseek-api-key-here"
)
DEEPSEEK_BASE_URL = os.environ.get(
    "DEEPSEEK_BASE_URL",
    "https://api.deepseek.com"
)
DEEPSEEK_MODEL = os.environ.get(
    "DEEPSEEK_MODEL",
    "deepseek-v4-flash"  # or deepseek-v4-pro
)

# ASR — faster-whisper
WHISPER_MODEL_SIZE = "base"  # tiny/base/small

# Cleanup
MAX_TASK_AGE_SECONDS = 86400  # 24h
