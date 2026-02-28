from __future__ import annotations

import time
from collections import defaultdict
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import Message

from src.utils.logger import log


class RateLimitMiddleware(BaseMiddleware):
    def __init__(self, limit: int = 5, window: int = 60) -> None:
        self._limit = limit
        self._window = window
        self._users: dict[int, list[float]] = defaultdict(list)

    async def __call__(
        self,
        handler: Callable[[Message, dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: dict[str, Any],
    ) -> Any:
        if not isinstance(event, Message) or not event.from_user:
            return await handler(event, data)

        uid = event.from_user.id
        now = time.monotonic()

        self._users[uid] = [
            t for t in self._users[uid] if now - t < self._window
        ]

        if len(self._users[uid]) >= self._limit:
            log.warning("rate_limited", user_id=uid)
            await event.answer(
                f"⏳ Dakikada en fazla {self._limit} arama yapabilirsin. "
                "Biraz bekleyip tekrar dene."
            )
            return None

        self._users[uid].append(now)
        return await handler(event, data)
