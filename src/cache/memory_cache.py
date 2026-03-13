from __future__ import annotations

from dataclasses import dataclass
from src.utils.logger import log


@dataclass
class CacheEntry:
    file_id: str
    file_name: str
    file_size: int
    source_chat: str
    message_id: int


class MemoryCache:
    def __init__(self) -> None:
        self._cache: dict[str, list[CacheEntry]] = {}

    async def lookup_many(self, norm_query: str, limit: int = 500) -> list[dict] | None:
        """
        Return cached results matching the normalized query prefix, up to limit.
        """
        results = []
        for cached_query, entries in self._cache.items():
            if norm_query in cached_query:
                for entry in entries:
                    if len(results) >= limit:
                        break
                    # We just use a dict format similar to what supabase did
                    results.append({
                        "file_id": entry.file_id,
                        "file_name": entry.file_name,
                        "file_size": entry.file_size,
                        "source_chat": entry.source_chat,
                        "message_id": entry.message_id,
                    })
                if len(results) >= limit:
                    break

        if not results:
            log.info("memory_cache_miss", query=norm_query)
            return None

        log.info("memory_cache_hit", query=norm_query, count=len(results))
        return results

    async def store(
        self,
        query: str,
        norm_query: str,
        file_id: str,
        file_name: str,
        file_size: int,
        source_chat: str,
        message_id: int,
    ) -> None:
        if norm_query not in self._cache:
            self._cache[norm_query] = []

        # Simple dedup strategy based on file_id
        for existing in self._cache[norm_query]:
            if existing.file_id == file_id:
                return

        entry = CacheEntry(
            file_id=file_id,
            file_name=file_name,
            file_size=file_size,
            source_chat=source_chat,
            message_id=message_id,
        )
        self._cache[norm_query].append(entry)
