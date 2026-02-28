from __future__ import annotations

import os
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv()


def _require(key: str) -> str:
    val = os.getenv(key)
    if not val:
        raise RuntimeError(f"Missing required env var: {key}")
    return val


def _parse_chats(raw: str) -> list[str | int]:
    result: list[str | int] = []
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            result.append(int(part))
        except ValueError:
            result.append(part)
    return result


@dataclass(frozen=True)
class Config:
    bot_token: str = field(default_factory=lambda: _require("BOT_TOKEN"))
    api_id: int = field(default_factory=lambda: int(_require("PYROGRAM_API_ID")))
    api_hash: str = field(default_factory=lambda: _require("PYROGRAM_API_HASH"))
    session_name: str = field(
        default_factory=lambda: os.getenv("PYROGRAM_SESSION_NAME", "book_finder_session")
    )
    supabase_url: str = field(default_factory=lambda: _require("SUPABASE_URL"))
    supabase_key: str = field(default_factory=lambda: _require("SUPABASE_KEY"))
    target_chats: list[str | int] = field(
        default_factory=lambda: _parse_chats(os.getenv("TARGET_CHATS", ""))
    )
    rate_limit: int = field(
        default_factory=lambda: int(os.getenv("RATE_LIMIT_PER_MINUTE", "5"))
    )
    max_results: int = field(
        default_factory=lambda: int(os.getenv("MAX_RESULTS", "5"))
    )


config = Config()
