from __future__ import annotations

import time
from dataclasses import dataclass, field
from src.utils.logger import log


@dataclass
class CacheEntry:
    file_id: str
    file_name: str
    file_size: int
    source_chat: str
    message_id: int
    created_at: float = field(default_factory=time.time)


class MemoryCache:
    def __init__(self, ttl_hours: float = 12.0) -> None:
        self._cache: dict[str, list[CacheEntry]] = {}
        self._ttl_seconds = ttl_hours * 3600
        self._hits = 0
        self._misses = 0

    @property
    def stats(self) -> dict:
        total = self._hits + self._misses
        hit_rate = (self._hits / total * 100) if total > 0 else 0
        total_entries = sum(len(v) for v in self._cache.values())
        return {
            "total_entries": total_entries,
            "total_queries": len(self._cache),
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": f"{hit_rate:.1f}%",
        }

    async def lookup_many(self, norm_query: str, limit: int = 500) -> list[dict] | None:
        now = time.time()
        results = []

        for cached_query, entries in self._cache.items():
            if norm_query in cached_query:
                for entry in entries:
                    if now - entry.created_at > self._ttl_seconds:
                        continue
                    if len(results) >= limit:
                        break
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
            self._misses += 1
            log.info("memory_cache_miss", query=norm_query)
            return None

        self._hits += 1
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

    async def cleanup_expired(self) -> int:
        """Süresi dolmuş cache entry'lerini temizle. Temizlenen sayıyı döndürür."""
        now = time.time()
        cleaned = 0

        keys_to_delete: list[str] = []
        for query_key, entries in self._cache.items():
            original_len = len(entries)
            self._cache[query_key] = [
                e for e in entries if now - e.created_at <= self._ttl_seconds
            ]
            cleaned += original_len - len(self._cache[query_key])

            if not self._cache[query_key]:
                keys_to_delete.append(query_key)

        for k in keys_to_delete:
            del self._cache[k]

        if cleaned > 0:
            log.info("cache_cleanup", removed=cleaned, remaining_queries=len(self._cache))

        return cleaned

    async def clear(self) -> int:
        """Tüm cache'i temizle."""
        count = sum(len(v) for v in self._cache.values())
        self._cache.clear()
        self._hits = 0
        self._misses = 0
        log.info("cache_cleared", removed=count)
        return count
