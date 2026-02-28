from __future__ import annotations

import os
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.filters import CommandStart, Command

from src.search.engine import SearchEngine
from src.search.telegram_source import TelegramSource
from src.bot.keyboards import (
    results_keyboard,
    after_download_keyboard,
    downloading_keyboard,
    ITEMS_PER_PAGE,
)
from src.utils.logger import log

router = Router()

_user_sessions: dict[int, dict] = {}

WELCOME_TEXT = (
    "━━━━━━━━━━━━━━━━━━━━━━\n"
    "📚 <b>BookFinder Bot</b>\n"
    "━━━━━━━━━━━━━━━━━━━━━━\n\n"
    "Merhaba! 👋 Ben kitap arama botuyum.\n\n"
    "Bana bir kitap adı, yazar veya konu yaz —\n"
    "Telegram kaynaklarında PDF olarak arayıp\n"
    "sana getireyim. ⚡\n\n"
    "┌─────────────────────\n"
    "│ 📝 <b>Örnek Aramalar:</b>\n"
    "│\n"
    "│ <code>TYT Matematik</code>\n"
    "│ <code>AYT Fizik Deneme</code>\n"
    "│ <code>3D Yayınları Biyoloji</code>\n"
    "└─────────────────────\n\n"
    "📌 Yardım → /help"
)

HELP_TEXT = (
    "━━━━━━━━━━━━━━━━━━━━━━\n"
    "❓ <b>Nasıl Kullanılır?</b>\n"
    "━━━━━━━━━━━━━━━━━━━━━━\n\n"
    "1️⃣ Kitap/konu adını yaz\n"
    "2️⃣ Ben kaynaklarda arayayım\n"
    "3️⃣ Sonuçları listeden gör\n"
    "4️⃣ İstediğine tıkla, PDF gelsin!\n\n"
    "┌─────────────────────\n"
    "│ ⚡ <b>Özellikler</b>\n"
    "│\n"
    "│ 📄 Sayfa sayfa sonuç gezme\n"
    "│ 💾 Önbellek ile hızlı erişim\n"
    "│ 📤 Dosya paylaşma\n"
    "│ 🔒 Dakikada 5 arama limiti\n"
    "└─────────────────────\n\n"
    "📌 Herhangi bir metin yaz ve aramaya başla!"
)

SEARCHING_TEXT = (
    "━━━━━━━━━━━━━━━━━━━━━━\n"
    "🔍 <b>Aranıyor...</b>\n"
    "━━━━━━━━━━━━━━━━━━━━━━\n\n"
    "📂 Kaynaklarda taranıyor\n"
    "⏳ Lütfen bekle..."
)


def _build_results_header(query: str, total: int, from_cache: bool) -> str:
    source = "⚡ Önbellek" if from_cache else "🌐 Canlı Arama"
    return (
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📚 <b>Arama Sonuçları</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🔎 <b>Sorgu:</b> <code>{query}</code>\n"
        f"📊 <b>{total}</b> sonuç bulundu ({source})\n\n"
        "İndirmek için dosyaya tıkla ⬇️"
    )


NOT_FOUND_TEXT = (
    "━━━━━━━━━━━━━━━━━━━━━━\n"
    "😔 <b>Sonuç Bulunamadı</b>\n"
    "━━━━━━━━━━━━━━━━━━━━━━\n\n"
    "Bu arama ile eşleşen PDF bulamadım.\n\n"
    "┌─────────────────────\n"
    "│ 💡 <b>İpuçları:</b>\n"
    "│\n"
    "│ • Farklı anahtar kelimeler dene\n"
    "│ • Kitap adını kısalt\n"
    "│ • Konu ya da yayınevi ile ara\n"
    "└─────────────────────"
)


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    await message.answer(WELCOME_TEXT, parse_mode="HTML")


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(HELP_TEXT, parse_mode="HTML")


@router.message(F.text & ~F.text.startswith("/"))
async def handle_search(message: Message, search_engine: SearchEngine) -> None:
    query = message.text.strip()
    if len(query) < 2:
        await message.answer("🔤 Lütfen en az 2 karakter gir.")
        return

    if len(query) > 200:
        await message.answer("✂️ Arama terimi çok uzun, kısaltmayı dene.")
        return

    uid = message.from_user.id
    status_msg = await message.answer(SEARCHING_TEXT, parse_mode="HTML")

    try:
        result = await search_engine.search(query)
    except Exception as exc:
        log.error("search_error", query=query, error=str(exc))
        await status_msg.edit_text("❌ Arama sırasında bir hata oluştu. Lütfen tekrar dene.")
        return

    if not result.results:
        await status_msg.edit_text(NOT_FOUND_TEXT, parse_mode="HTML")
        return

    result_items = [
        {"file_name": r.file_name, "file_size": r.file_size}
        for r in result.results
    ]

    _user_sessions[uid] = {
        "query": query,
        "results": result.results,
        "result_items": result_items,
        "from_cache": result.from_cache,
        "total": result.total,
        "page": 0,
    }

    header = _build_results_header(query, result.total, result.from_cache)
    await status_msg.edit_text(
        header,
        parse_mode="HTML",
        reply_markup=results_keyboard(result_items, page=0, total=result.total),
    )


@router.callback_query(F.data.startswith("page:"))
async def handle_page(callback: CallbackQuery) -> None:
    uid = callback.from_user.id
    session = _user_sessions.get(uid)
    if not session:
        await callback.answer("⚠️ Oturum süresi doldu, tekrar ara.", show_alert=True)
        return

    page = int(callback.data.split(":")[1])
    session["page"] = page

    header = _build_results_header(session["query"], session["total"], session["from_cache"])
    await callback.message.edit_text(
        header,
        parse_mode="HTML",
        reply_markup=results_keyboard(session["result_items"], page=page, total=session["total"]),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("dl:"))
async def handle_download(
    callback: CallbackQuery, bot: Bot, telegram_source: TelegramSource
) -> None:
    uid = callback.from_user.id
    session = _user_sessions.get(uid)
    if not session:
        await callback.answer("⚠️ Oturum süresi doldu, tekrar ara.", show_alert=True)
        return

    idx = int(callback.data.split(":")[1])
    results = session["results"]
    if idx >= len(results):
        await callback.answer("⚠️ Sonuç bulunamadı.", show_alert=True)
        return

    r = results[idx]
    await callback.answer("📥 Dosya indiriliyor, lütfen bekle...")

    progress_msg = await callback.message.answer(
        f"⬇️ <b>İndiriliyor:</b> {r.file_name}\n⏳ Lütfen bekle...",
        parse_mode="HTML",
        reply_markup=downloading_keyboard(),
    )

    try:
        file_path = await telegram_source.download_file(r.chat_id, r.message_id)
        if not file_path:
            await progress_msg.edit_text("❌ Dosya indirilemedi. Kaynak silinmiş olabilir.")
            return

        await progress_msg.edit_text(
            f"📤 <b>Gönderiliyor:</b> {r.file_name}\n⏳ Lütfen bekle...",
            parse_mode="HTML",
        )

        doc = FSInputFile(file_path, filename=r.file_name)
        size_mb = r.file_size / (1024 * 1024)

        await bot.send_document(
            chat_id=uid,
            document=doc,
            caption=(
                f"━━━━━━━━━━━━━━━━━━━━━━\n"
                f"📄 <b>{r.file_name}</b>\n"
                f"📊 {size_mb:.1f} MB\n"
                f"━━━━━━━━━━━━━━━━━━━━━━"
            ),
            parse_mode="HTML",
            reply_markup=after_download_keyboard(r.file_name),
        )

        await progress_msg.delete()

        try:
            os.unlink(file_path)
            os.rmdir(os.path.dirname(file_path))
        except OSError:
            pass

    except Exception as exc:
        log.error("send_failed", file=r.file_name, error=str(exc))
        await progress_msg.edit_text(
            "❌ Dosya gönderilemedi. Dosya çok büyük veya kaynak silinmiş olabilir."
        )


@router.callback_query(F.data == "new_search")
async def handle_new_search(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.answer(
        "🔍 Yeni bir kitap/konu adı yaz, aramaya başlayalım!",
        parse_mode="HTML",
    )


@router.callback_query(F.data == "noop")
async def handle_noop(callback: CallbackQuery) -> None:
    await callback.answer()
