from __future__ import annotations

import asyncio
import signal

from aiogram import Bot, Dispatcher
from pyrogram import Client as PyroClient

from src.config import config
from src.cache.memory_cache import MemoryCache
from src.search.telegram_source import TelegramSource
from src.search.engine import SearchEngine
from src.bot.handlers import router
from src.bot.middlewares import RateLimitMiddleware
from src.utils.logger import log


async def _periodic_cache_cleanup(cache: MemoryCache, interval: int = 600) -> None:
    """Her 10 dakikada süresi dolmuş cache entry'lerini temizle."""
    while True:
        await asyncio.sleep(interval)
        try:
            removed = await cache.cleanup_expired()
            if removed:
                stats = cache.stats
                log.info(
                    "periodic_cleanup_done",
                    removed=removed,
                    total_entries=stats["total_entries"],
                    hit_rate=stats["hit_rate"],
                )
        except Exception as exc:
            log.error("cleanup_error", error=str(exc))


async def main() -> None:
    log.info(
        "bot_starting",
        target_chats=config.target_chats,
        cache_ttl_hours=config.cache_ttl_hours,
        search_timeout=config.search_timeout,
        session_ttl_minutes=config.session_ttl_minutes,
    )

    bot = Bot(token=config.bot_token)

    pyro = PyroClient(
        name=config.session_name,
        api_id=config.api_id,
        api_hash=config.api_hash,
    )

    cache = MemoryCache(ttl_hours=config.cache_ttl_hours)
    source = TelegramSource(
        pyro,
        config.target_chats,
        config.dump_channel_id,
        search_timeout=config.search_timeout,
    )
    engine = SearchEngine(cache, source, max_results=config.max_results)

    dp = Dispatcher()
    dp.message.middleware(RateLimitMiddleware(limit=config.rate_limit))
    dp.include_router(router)

    stop = asyncio.Event()

    def _signal_handler() -> None:
        log.info("shutdown_signal_received")
        stop.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, _signal_handler)

    await pyro.start()
    log.info("pyrogram_started", session=config.session_name)

    cleanup_task = asyncio.create_task(_periodic_cache_cleanup(cache))

    try:
        polling_task = asyncio.create_task(
            dp.start_polling(bot, search_engine=engine, telegram_source=source)
        )
        await stop.wait()
    finally:
        log.info("bot_shutting_down")
        cleanup_task.cancel()
        await dp.stop_polling()
        polling_task.cancel()
        await pyro.stop()
        await bot.session.close()
        stats = cache.stats
        log.info("bot_stopped", cache_stats=stats)


if __name__ == "__main__":
    asyncio.run(main())
