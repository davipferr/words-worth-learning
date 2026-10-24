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


# Han characters, kana and the prolonged-sound mark: scripts written without spaces.
_CJK = re.compile(r"[぀-ヿ㐀-䶿一-鿿豈-﫿々ー]+")
MAX_WORD = 8  # longest dictionary word tried by the segmenter, in characters


def is_cjk(text: str) -> bool:
    return bool(_CJK.search(text))


def segment(run: str, vocab: set[str]) -> list[str]:
    """Split a run of Chinese or Japanese characters into known words, longest
    match first (forward maximum matching); unknown characters stand alone.

    >>> segment("我们知道", {"我们", "知道", "我"})
    ['我们', '知道']
    """
    out, i = [], 0
    while i < len(run):
        for n in range(min(MAX_WORD, len(run) - i), 0, -1):
            if n == 1 or run[i : i + n] in vocab:
                out.append(run[i : i + n])
                i += n
                break
    return out


def tokenize_cjk(text: str, vocab: set[str]) -> list[str]:
    """Tokens of a Chinese or Japanese sentence: CJK runs segmented against
    ``vocab`` (the language's frequency-list forms), Latin words as usual."""
    out: list[str] = []
    pos = 0
    for m in _CJK.finditer(text):
        out += tokenize(text[pos : m.start()])
        out += segment(m.group(0), vocab)
        pos = m.end()
    return out + tokenize(text[pos:])


def is_word(token: str) -> bool:
    """True for tokens made of letters (and apostrophes), as kept from the frequency lists."""
    return bool(token) and all(ch.isalpha() or ch == "'" for ch in token) and any(ch.isalpha() for ch in token)


def fold(word: str) -> str:
    """Lower case without diacritics: "Información" -> "informacion", "Straße" -> "strasse".

    Chinese and Japanese are only lower-cased: decomposing kana would strip the
    voicing marks that tell が from か."""
    if is_cjk(word):
        return unicodedata.normalize("NFC", word.lower())
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
