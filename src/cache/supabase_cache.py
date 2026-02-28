from __future__ import annotations

from supabase import create_client, Client
from src.utils.logger import log

TABLE = "searched_books"


class SupabaseCache:
    def __init__(self, url: str, key: str) -> None:
        self._client: Client = create_client(url, key)
        log.info("supabase_connected")

    async def lookup(self, norm_query: str) -> dict | None:
        resp = (
            self._client.table(TABLE)
            .select("*")
            .eq("norm_query", norm_query)
            .order("hit_count", desc=True)
            .limit(1)
            .execute()
        )
        if resp.data:
            row = resp.data[0]
            self._increment_hit(row["id"])
            log.info("cache_hit", query=norm_query, file_id=row["file_id"])
            return row
        return None

    async def lookup_many(self, norm_query: str, limit: int = 5) -> list[dict]:
        resp = (
            self._client.table(TABLE)
            .select("*")
            .ilike("norm_query", f"%{norm_query}%")
            .order("hit_count", desc=True)
            .limit(limit)
            .execute()
        )
        if resp.data:
            log.info("cache_hit_many", query=norm_query, count=len(resp.data))
        return resp.data or []

    async def store(
        self,
        query: str,
        norm_query: str,
        file_id: str,
        file_name: str | None = None,
        file_size: int | None = None,
        source_chat: str | None = None,
    ) -> None:
        existing = (
            self._client.table(TABLE)
            .select("id")
            .eq("file_id", file_id)
            .limit(1)
            .execute()
        )
        if existing.data:
            return

        self._client.table(TABLE).insert(
            {
                "query": query,
                "norm_query": norm_query,
                "file_id": file_id,
                "file_name": file_name,
                "file_size": file_size,
                "source_chat": source_chat,
            }
        ).execute()
        log.info("cache_stored", query=query, file_id=file_id)

    def _increment_hit(self, row_id: int) -> None:
        self._client.rpc("increment_hit_count", {"row_id": row_id}).execute()
