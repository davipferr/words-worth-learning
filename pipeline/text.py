"""Text helpers: accent folding, tokenizing like the frequency lists, word similarity."""

from __future__ import annotations

import re
import unicodedata

# Letters only (no digits or underscore), with the apostrophe attached on the
# side each language's frequency list attaches it.
_WORD = r"[^\W\d_]+"
_TOKEN = {
    "right": re.compile(rf"'{_WORD}|{_WORD}"),
    "left": re.compile(rf"{_WORD}'|{_WORD}"),
    "none": re.compile(_WORD),
}
_APOSTROPHES = str.maketrans({"’": "'", "‘": "'", "ʼ": "'", "`": "'"})


def tokenize(text: str, apostrofo: str = "none") -> list[str]:
    """Lower-cased word tokens, split the way OpenSubtitles frequency lists are.

    >>> tokenize("Don't stop!", "right")
    ['don', "'t", 'stop']
    >>> tokenize("C'est la vie", "left")
    ["c'", 'est', 'la', 'vie']
    """
    return _TOKEN[apostrofo].findall(text.translate(_APOSTROPHES).lower())


def is_word(token: str) -> bool:
    """True for tokens made of letters (and apostrophes), as kept from the frequency lists."""
    return bool(token) and all(ch.isalpha() or ch == "'" for ch in token) and any(ch.isalpha() for ch in token)


def fold(word: str) -> str:
    """Lower case without diacritics: "Información" -> "informacion", "Straße" -> "strasse"."""
    s = unicodedata.normalize("NFKD", word.lower().replace("ß", "ss"))
    return "".join(ch for ch in s if not unicodedata.combining(ch))


def levenshtein(a: str, b: str) -> int:
    if len(a) < len(b):
        a, b = b, a
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def similarity(a: str, b: str) -> float:
    """1 - edit distance / longer length, on accent-folded words (1 = same spelling).

    "noche" vs "noite" -> 0.6; "family" vs "família" -> 0.86; "Hund" vs "cão" -> 0.
    """
    fa, fb = fold(a), fold(b)
    if not fa or not fb:
        return 0.0
    return 1 - levenshtein(fa, fb) / max(len(fa), len(fb))
