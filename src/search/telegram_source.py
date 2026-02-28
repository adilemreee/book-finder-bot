from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

from pyrogram import Client
from pyrogram.enums import MessageMediaType
from src.utils.logger import log


@dataclass
class SearchResult:
    file_name: str
    file_size: int
    chat_id: int | str
    message_id: int


class TelegramSource:
    def __init__(self, client: Client, target_chats: list[str | int]) -> None:
        self._client = client
        self._target_chats = target_chats

    async def search(self, query: str, max_results: int = 500) -> list[SearchResult]:
        results: list[SearchResult] = []
        seen: set[str] = set()

        for chat_id in self._target_chats:
            if len(results) >= max_results:
                break
            try:
                found = await self._search_chat(chat_id, query, max_results - len(results), seen)
                results.extend(found)
            except Exception as exc:
                log.warning("chat_search_failed", chat=chat_id, error=str(exc))
                continue

        return results

    async def _search_chat(
        self, chat_id: str | int, query: str, limit: int, seen: set[str]
    ) -> list[SearchResult]:
        results: list[SearchResult] = []

        async for msg in self._client.search_messages(chat_id, query=query, limit=limit * 3):
            if len(results) >= limit:
                break

            if msg.media != MessageMediaType.DOCUMENT:
                continue

            doc = msg.document
            if not doc:
                continue

            mime = doc.mime_type or ""
            file_name = doc.file_name or ""

            is_pdf = mime == "application/pdf" or file_name.lower().endswith(".pdf")
            if not is_pdf:
                continue

            dedup_key = f"{file_name}_{doc.file_size}"
            if dedup_key in seen:
                continue
            seen.add(dedup_key)

            results.append(
                SearchResult(
                    file_name=file_name or "kitap.pdf",
                    file_size=doc.file_size or 0,
                    chat_id=chat_id,
                    message_id=msg.id,
                )
            )
            log.info("pdf_found", chat=chat_id, file=file_name, size=doc.file_size)

        return results

    async def download_file(self, chat_id: str | int, message_id: int) -> str | None:
        try:
            tmp_dir = tempfile.mkdtemp(prefix="bookbot_")
            msg = await self._client.get_messages(chat_id, message_id)
            if not msg or not msg.document:
                return None

            file_path = await self._client.download_media(
                msg, file_name=os.path.join(tmp_dir, msg.document.file_name or "kitap.pdf")
            )
            log.info("file_downloaded", path=file_path)
            return file_path
        except Exception as exc:
            log.error("download_error", chat=chat_id, msg_id=message_id, error=str(exc))
            return None
