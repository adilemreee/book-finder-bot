import re
import unicodedata

_TR_MAP = str.maketrans("çğıöşüÇĞİÖŞÜ", "cgiosuCGIOSU")
_MULTI_SPACE = re.compile(r"\s+")


def normalize_query(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    text = text.translate(_TR_MAP)
    text = text.lower().strip()
    text = _MULTI_SPACE.sub(" ", text)
    return text
