from __future__ import annotations

import base64
import hashlib
from functools import lru_cache
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken

from bot.config import Config

_PREFIX = "enc:"


def _derive_key(seed: str) -> bytes:
    digest = hashlib.sha256(seed.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)


@lru_cache(maxsize=1)
def _get_fernet_candidates() -> tuple[Fernet, ...]:
    candidates: list[Fernet] = []

    if Config.DATA_ENCRYPTION_KEY:
        try:
            candidates.append(Fernet(Config.DATA_ENCRYPTION_KEY.encode("utf-8")))
        except ValueError:
            pass

    hardened_seed = "|".join(
        value
        for value in [
            Config.BOT_TOKEN,
            Config.PANEL_PASSWORD,
            str(Config.OWNER_ID or ""),
            str(Config.CHANNEL_ID or ""),
        ]
        if value
    ) or "hatekadeh-default-key"
    candidates.append(Fernet(_derive_key(hardened_seed)))

    legacy_seed = Config.BOT_TOKEN or Config.PANEL_PASSWORD or "hatekadeh-default-key"
    legacy_candidate = Fernet(_derive_key(legacy_seed))
    if legacy_candidate not in candidates:
        candidates.append(legacy_candidate)

    return tuple(candidates)


def encrypt_value(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None

    fernet = _get_fernet_candidates()[0]
    token = fernet.encrypt(value.encode("utf-8")).decode("utf-8")
    return f"{_PREFIX}{token}"


def decrypt_value(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None

    if not value.startswith(_PREFIX):
        return value

    token = value[len(_PREFIX):].encode("utf-8")
    for fernet in _get_fernet_candidates():
        try:
            return fernet.decrypt(token).decode("utf-8")
        except InvalidToken:
            continue
    return value[len(_PREFIX):]
