from __future__ import annotations

import asyncio
import signal

from aiogram import Bot, Dispatcher
from pyrogram import Client as PyroClient

from src.config import config
from src.cache.supabase_cache import SupabaseCache
from src.search.telegram_source import TelegramSource
from src.search.engine import SearchEngine
from src.bot.handlers import router
from src.bot.middlewares import RateLimitMiddleware
from src.utils.logger import log


async def main() -> None:
    log.info("bot_starting", target_chats=config.target_chats)

    bot = Bot(token=config.bot_token)

    pyro = PyroClient(
        name=config.session_name,
        api_id=config.api_id,
        api_hash=config.api_hash,
    )

    cache = SupabaseCache(config.supabase_url, config.supabase_key)
    source = TelegramSource(pyro, config.target_chats)
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

    try:
        polling_task = asyncio.create_task(
            dp.start_polling(bot, search_engine=engine, telegram_source=source)
        )
        await stop.wait()
    finally:
        log.info("bot_shutting_down")
        await dp.stop_polling()
        polling_task.cancel()
        await pyro.stop()
        await bot.session.close()
        log.info("bot_stopped")


if __name__ == "__main__":
    asyncio.run(main())
