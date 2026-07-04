import re
import logging
from datetime import datetime, timedelta, timezone

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TEHRAN_OFFSET = timedelta(hours=3, minutes=30)

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
    return datetime.utcnow() + TEHRAN_OFFSET


def format_tehran_datetime(value: datetime | None) -> str:
    if value is None:
        return ""
    if value.tzinfo is not None:
        value = value.astimezone(timezone.utc).replace(tzinfo=None) + TEHRAN_OFFSET
    return value.strftime("%Y-%m-%d %H:%M:%S")