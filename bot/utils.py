import re
import logging
import time
from datetime import datetime, timedelta, timezone

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TEHRAN_OFFSET = timedelta(hours=3, minutes=30)

# Simple in-memory rate limiter: user_id -> list of timestamps
_rate_limit_buckets: dict[int, list[float]] = {}


def is_rate_limited(user_id: int, window_seconds: float = 5.0, max_requests: int = 3) -> bool:
    """Return True if the user has exceeded the rate limit.
    Uses a sliding window of `window_seconds` allowing at most `max_requests`.
    """
    now = time.monotonic()
    bucket = _rate_limit_buckets.get(user_id, [])
    cutoff = now - window_seconds
    bucket = [t for t in bucket if t > cutoff]
    if len(bucket) >= max_requests:
        _rate_limit_buckets[user_id] = bucket
        return True
    bucket.append(now)
    _rate_limit_buckets[user_id] = bucket
    return False

def is_admin(user_id: int, admin_list: list) -> bool:
    return user_id in admin_list

def escape_markdown(text: str) -> str:
    if not text:
        return ""
    escape_chars = r'_*[]()~`>#+-=|{}.!'
    return re.sub(f'([{re.escape(escape_chars)}])', r'\\\1', text)

def truncate(text: str, length: int = 100) -> str:
    if len(text) > length:
        return text[:length] + "..."
    return text


def now_tehran() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None) + TEHRAN_OFFSET


def format_tehran_datetime(value: datetime | None) -> str:
    if value is None:
        return ""
    if value.tzinfo is not None:
        value = value.astimezone(timezone.utc).replace(tzinfo=None) + TEHRAN_OFFSET
    return value.strftime("%Y-%m-%d %H:%M:%S")