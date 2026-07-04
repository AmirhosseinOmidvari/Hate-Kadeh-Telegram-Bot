import os
from dotenv import load_dotenv

load_dotenv()


def _int_env(name: str, default: int = 0) -> int:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _bool_env(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}

class Config:
    BOT_TOKEN = os.getenv("BOT_TOKEN", "")
    BOT_USERNAME = os.getenv("BOT_USERNAME")
    CHANNEL_ID = _int_env("CHANNEL_ID")
    ADMIN_IDS = [int(id.strip()) for id in os.getenv("ADMIN_IDS", "").split(",") if id.strip()]
    OWNER_ID = _int_env("OWNER_ID")
    PANEL_PASSWORD = os.getenv("PANEL_PASSWORD", "admin123")
    DATA_ENCRYPTION_KEY = os.getenv("DATA_ENCRYPTION_KEY")
    PROXY_URL = os.getenv("PROXY_URL")
    SESSION_TTL_SECONDS = _int_env("SESSION_TTL_SECONDS", 43200)
    LOGIN_WINDOW_SECONDS = _int_env("LOGIN_WINDOW_SECONDS", 600)
    MAX_LOGIN_ATTEMPTS = _int_env("MAX_LOGIN_ATTEMPTS", 5)
    COOKIE_SECURE = _bool_env("COOKIE_SECURE", False)
    DATABASE_URL = "sqlite:///hatekadeh.db"
    SEND_RETRIES = _int_env("SEND_RETRIES", 3)
    SEND_BACKOFF_BASE = float(os.getenv("SEND_BACKOFF_BASE", "0.5"))
    MAX_CONCURRENT_SENDS = _int_env("MAX_CONCURRENT_SENDS", 3)
    RATE_LIMIT = float(os.getenv("RATE_LIMIT", "5.0"))