from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

ITEMS_PER_PAGE = 5


def results_keyboard(
    results: list[dict], page: int = 0, total: int = 0
) -> InlineKeyboardMarkup:
    start = page * ITEMS_PER_PAGE
    end = min(start + ITEMS_PER_PAGE, len(results))
    page_items = results[start:end]
    total_pages = (len(results) + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE

    buttons: list[list[InlineKeyboardButton]] = []

    for i, r in enumerate(page_items):
        idx = start + i
        name = r.get("file_name", "kitap.pdf")
        size_mb = r.get("file_size", 0) / (1024 * 1024)

        if len(name) > 60:
            name = name[:57] + "..."

        label = f"📄 {name} • {size_mb:.1f} MB"
        buttons.append([InlineKeyboardButton(text=label, callback_data=f"dl:{idx}")])

    nav_row: list[InlineKeyboardButton] = []
    if page > 0:
        nav_row.append(InlineKeyboardButton(text="◀️ Önceki", callback_data=f"page:{page - 1}"))

    nav_row.append(
        InlineKeyboardButton(text=f"📖 {page + 1}/{total_pages}", callback_data="noop")
    )

    if end < len(results):
        nav_row.append(InlineKeyboardButton(text="Sonraki ▶️", callback_data=f"page:{page + 1}"))

    buttons.append(nav_row)

    info_text = f"🔎 Toplam {total} sonuç bulundu"
    buttons.append([InlineKeyboardButton(text=info_text, callback_data="noop")])

    buttons.append([
        InlineKeyboardButton(text="🔍 Yeni Arama", callback_data="new_search"),
    ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def downloading_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⏳ İndiriliyor...", callback_data="noop")]
        ]
    )


def after_download_keyboard(file_name: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🔍 Yeni Arama", callback_data="new_search"),
                InlineKeyboardButton(text="📤 Paylaş", switch_inline_query=file_name[:50]),
            ]
        ]
    )
