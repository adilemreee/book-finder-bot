from __future__ import annotations

import time
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command

from src.config import config
from src.search.engine import SearchEngine
from src.search.telegram_source import TelegramSource
from src.bot.keyboards import (
    results_keyboard,
    after_download_keyboard,
    downloading_keyboard,
    category_keyboard,
    ITEMS_PER_PAGE,
)
from src.utils.logger import log
from src.utils.categorizer import detect_categories, CATEGORY_MAP

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
    "📌 Yardım → /help\n"
    "📂 Kategoriler → /kategori"
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
    "│ 📂 Kategori ile filtreleme\n"
    "│ ⚡ Paralel hızlı tarama\n"
    "└─────────────────────\n\n"
    "📌 Herhangi bir metin yaz ve aramaya başla!\n"
    "📂 /kategori → Kategorilere göz at"
)

SEARCHING_TEXT = (
    "━━━━━━━━━━━━━━━━━━━━━━\n"
    "🔍 <b>Aranıyor...</b>\n"
    "━━━━━━━━━━━━━━━━━━━━━━\n\n"
    "📂 Kaynaklarda taranıyor\n"
    "⏳ Lütfen bekle..."
)

CATEGORY_TEXT = (
    "━━━━━━━━━━━━━━━━━━━━━━\n"
    "📂 <b>Kategoriler</b>\n"
    "━━━━━━━━━━━━━━━━━━━━━━\n\n"
    "Bir kategori seç, ilgili kitapları\n"
    "hemen arayalım ⬇️"
)


def _build_results_header(query: str, total: int, from_cache: bool, category: str | None = None) -> str:
    source = "⚡ Önbellek" if from_cache else "🌐 Canlı Arama"
    cat_line = f"\n📂 <b>Kategori:</b> {category}" if category else ""
    return (
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📚 <b>Arama Sonuçları</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🔎 <b>Sorgu:</b> <code>{query}</code>\n"
        f"📊 <b>{total}</b> sonuç bulundu ({source})"
        f"{cat_line}\n\n"
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
    "│ • /kategori ile kategorilere bak\n"
    "└─────────────────────"
)


def _cleanup_expired_sessions() -> int:
    """Süresi dolmuş user session'larını temizle."""
    now = time.time()
    ttl = config.session_ttl_minutes * 60
    expired = [
        uid for uid, s in _user_sessions.items()
        if now - s.get("created_at", 0) > ttl
    ]
    for uid in expired:
        del _user_sessions[uid]
    return len(expired)


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    await message.answer(WELCOME_TEXT, parse_mode="HTML")


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(HELP_TEXT, parse_mode="HTML")


@router.message(Command("kategori"))
async def cmd_category(message: Message) -> None:
    await message.answer(
        CATEGORY_TEXT,
        parse_mode="HTML",
        reply_markup=category_keyboard(),
    )


@router.callback_query(F.data.startswith("cat:"))
async def handle_category_select(
    callback: CallbackQuery, search_engine: SearchEngine
) -> None:
    category = callback.data.split(":", 1)[1]
    await callback.answer(f"🔍 {category} aranıyor...")

    keywords = CATEGORY_MAP.get(category, [])
    if not keywords:
        await callback.message.answer("⚠️ Kategori bulunamadı.")
        return

    query = keywords[0]
    uid = callback.from_user.id

    status_msg = await callback.message.answer(SEARCHING_TEXT, parse_mode="HTML")

    try:
        result = await search_engine.search(query)
    except Exception as exc:
        log.error("category_search_error", category=category, error=str(exc))
        await status_msg.edit_text("❌ Arama sırasında bir hata oluştu.")
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
        "category": category,
        "created_at": time.time(),
    }

    header = _build_results_header(query, result.total, result.from_cache, category=category)
    await status_msg.edit_text(
        header,
        parse_mode="HTML",
        reply_markup=results_keyboard(result_items, page=0, total=result.total),
    )


@router.message(F.text & ~F.text.startswith("/"))
async def handle_search(message: Message, search_engine: SearchEngine) -> None:
    query = message.text.strip()
    if len(query) < 2:
        await message.answer("🔤 Lütfen en az 2 karakter gir.")
        return

    if len(query) > 200:
        await message.answer("✂️ Arama terimi çok uzun, kısaltmayı dene.")
        return

    # Eski session'ları temizle
    cleaned = _cleanup_expired_sessions()
    if cleaned:
        log.info("sessions_cleaned", count=cleaned)

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
        "category": None,
        "created_at": time.time(),
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

    header = _build_results_header(
        session["query"], session["total"], session["from_cache"],
        category=session.get("category"),
    )
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
        dump_msg_id = await telegram_source.copy_to_dump(r.chat_id, r.message_id)
        if not dump_msg_id:
            await progress_msg.edit_text(
                "❌ Dosya indirilemedi. Kaynak silinmiş olabilir.",
                reply_markup=_retry_keyboard(idx),
            )
            return

        size_mb = r.file_size / (1024 * 1024)

        cats = detect_categories(r.file_name)
        cat_line = f"📂 {', '.join(cats)}\n" if cats else ""

        caption = (
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📄 <b>{r.file_name}</b>\n"
            f"📊 {size_mb:.1f} MB\n"
            f"{cat_line}"
            f"━━━━━━━━━━━━━━━━━━━━━━"
        )

        await bot.copy_message(
            chat_id=uid,
            from_chat_id=config.dump_channel_id,
            message_id=dump_msg_id,
            caption=caption,
            parse_mode="HTML",
            reply_markup=after_download_keyboard(r.file_name),
        )

        await progress_msg.delete()

    except Exception as exc:
        log.error("send_failed", file=r.file_name, error=str(exc))
        await progress_msg.edit_text(
            "❌ Dosya gönderilemedi. Dosya çok büyük veya kaynak silinmiş olabilir.",
            reply_markup=_retry_keyboard(idx),
        )


def _retry_keyboard(idx: int):
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Tekrar Dene", callback_data=f"dl:{idx}")],
            [InlineKeyboardButton(text="🔍 Yeni Arama", callback_data="new_search")],
        ]
    )


@router.callback_query(F.data == "new_search")
async def handle_new_search(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.answer(
        "🔍 Yeni bir kitap/konu adı yaz, aramaya başlayalım!\n"
        "📂 Kategoriler → /kategori",
        parse_mode="HTML",
    )


@router.callback_query(F.data == "noop")
async def handle_noop(callback: CallbackQuery) -> None:
    await callback.answer()
