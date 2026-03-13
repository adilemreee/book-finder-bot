from __future__ import annotations

import re

CATEGORY_MAP: dict[str, list[str]] = {
    "📐 Matematik": ["matematik", "math", "calculus", "cebir", "geometri"],
    "🔬 Fizik": ["fizik", "physics"],
    "🧪 Kimya": ["kimya", "chemistry"],
    "🧬 Biyoloji": ["biyoloji", "biology"],
    "📖 Türkçe": ["turkce", "türkçe", "edebiyat", "dil bilgisi", "paragraf"],
    "🌍 Tarih": ["tarih", "history", "inkılap", "inkilap"],
    "🗺️ Coğrafya": ["cografya", "coğrafya", "geography"],
    "🇬🇧 İngilizce": ["ingilizce", "english", "yds", "yokdil"],
    "📝 TYT": ["tyt"],
    "🎯 AYT": ["ayt"],
    "📚 LGS": ["lgs"],
    "🏛️ KPSS": ["kpss"],
    "📊 DGS": ["dgs"],
    "🎓 ALES": ["ales"],
    "📕 Roman": ["roman", "novel", "hikaye", "öykü"],
    "💼 Kişisel Gelişim": ["kişisel gelişim", "self help", "motivasyon"],
    "💻 Yazılım": ["python", "java", "programming", "yazılım", "kodlama", "c++", "javascript"],
    "📈 Ekonomi": ["ekonomi", "finans", "iktisat", "muhasebe"],
}

FORMAT_ICONS: dict[str, str] = {
    "pdf": "📄",
    "epub": "📱",
    "djvu": "📰",
    "mobi": "📲",
    "doc": "📝",
    "docx": "📝",
    "fb2": "📖",
    "azw3": "📲",
    "rtf": "📃",
    "txt": "📋",
}

_WORD_BOUNDARY = re.compile(r"[\s\-_.,()]+")


def detect_categories(file_name: str) -> list[str]:
    name_lower = file_name.lower()
    found: list[str] = []
    for category, keywords in CATEGORY_MAP.items():
        for kw in keywords:
            if kw in name_lower:
                found.append(category)
                break
    return found


def detect_format(file_name: str) -> str:
    ext = file_name.lower().rsplit(".", 1)[-1] if "." in file_name else ""
    return FORMAT_ICONS.get(ext, "📄")


def get_all_categories() -> list[str]:
    return list(CATEGORY_MAP.keys())


def parse_category_query(text: str) -> tuple[str | None, str]:
    """
    Parse query for category prefix.
    Examples:
      "kategori:matematik fizik 1" → ("📐 Matematik", "fizik 1")
      "normal arama"               → (None, "normal arama")
    """
    if ":" not in text:
        return None, text

    prefix, _, rest = text.partition(":")
    prefix = prefix.strip().lower()

    if prefix in ("kat", "kategori", "konu", "tür"):
        rest = rest.strip()
        keyword = rest.split()[0].lower() if rest else ""
        remaining = " ".join(rest.split()[1:]) if rest else ""

        for category, keywords in CATEGORY_MAP.items():
            for kw in keywords:
                if kw.startswith(keyword) or keyword.startswith(kw):
                    return category, remaining if remaining else keyword

    return None, text
