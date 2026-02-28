from __future__ import annotations

from dataclasses import dataclass

from src.cache.supabase_cache import SupabaseCache
from src.search.telegram_source import TelegramSource, SearchResult
from src.utils.normalizer import normalize_query
from src.utils.logger import log


@dataclass
class EngineResult:
    results: list[SearchResult]
    from_cache: bool
    total: int


class SearchEngine:
    def __init__(self, cache: SupabaseCache, source: TelegramSource, max_results: int = 500) -> None:
        self._cache = cache
        self._source = source
        self._max_results = max_results

    async def search(self, query: str) -> EngineResult:
        norm = normalize_query(query)
        log.info("search_start", query=query, norm=norm)

        cached = await self._cache.lookup_many(norm, limit=self._max_results)
        if cached:
            return EngineResult(
                results=[
                    SearchResult(
                        file_name=row.get("file_name", "kitap.pdf"),
                        file_size=row.get("file_size", 0),
                        chat_id=row.get("source_chat", ""),
                        message_id=row.get("message_id", 0),
                    )
                    for row in cached
                ],
                from_cache=True,
                total=len(cached),
            )

        live_results = await self._source.search(query, max_results=self._max_results)

        for r in live_results:
            await self._cache.store(
                query=query,
                norm_query=norm,
                file_id=f"{r.chat_id}:{r.message_id}",
                file_name=r.file_name,
                file_size=r.file_size,
                source_chat=str(r.chat_id),
            )

        return EngineResult(
            results=live_results,
            from_cache=False,
            total=len(live_results),
        )
