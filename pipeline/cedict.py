"""CC-CEDICT, the community Chinese–English dictionary (CC BY-SA 4.0).

Wiktionary groups each Chinese character's meanings by etymology, oldest
first, and attaches every reading to every group, so 的 comes out as "bright;
clear (dì)" instead of the possessive particle "de". CC-CEDICT has one line
per reading with short English definitions:

    說 说 [shuo1] /to speak; to talk; to say/to explain; to comment/

The reading a learner needs is the one the Chinese treebank uses for the word
(its ``LTranslit``); without one, the reading with the most real definitions
(not "variant of …" or "surname …").
"""

from __future__ import annotations

import io
import re
import unicodedata
import zipfile
from datetime import timedelta

import polars as pl

from .http import download
from .text import fold

URL = "https://www.mdbg.net/chinese/export/cedict/cedict_1_0_ts_utf-8_mdbg.zip"
MAX_AGE = timedelta(days=90)

_LINE = re.compile(r"^(\S+) (\S+) \[([^\]]+)\] /(.*)/\s*$")
# Definitions that describe the entry instead of giving its meaning.
_META = re.compile(r"^(variant of|old variant of|surname |used in |see |also written|japanese variant|abbr\. for|erhua variant|\(old\)|archaic variant)", re.I)
_MARKS = {"a": "āáǎà", "e": "ēéěè", "i": "īíǐì", "o": "ōóǒò", "u": "ūúǔù", "ü": "ǖǘǚǜ"}


def _syllable(s: str) -> str:
    """"shuo1" -> "shuō", "lu:4" -> "lǜ", "de5" -> "de"."""
    if not s or not s[-1].isdigit():
        return s
    tone, base = int(s[-1]), s[:-1].replace("u:", "ü").replace("v", "ü")
    if tone in (0, 5) or not base:
        return base
    # Tone mark goes on a/e, then on the o of "ou", else on the last vowel.
    low = base.lower()
    if "a" in low or "e" in low:
        i = low.index("a") if "a" in low else low.index("e")
    elif "ou" in low:
        i = low.index("o")
    else:
        i = max((j for j, ch in enumerate(low) if ch in _MARKS), default=-1)
    if i < 0:
        return base
    mark = _MARKS[low[i]][tone - 1]
    return base[:i] + (mark.upper() if base[i].isupper() else mark) + base[i + 1 :]


def pinyin(numbered: str) -> str:
    """"dian4 hua4" -> "diànhuà" (the spacing CEDICT uses between syllables is dropped)."""
    return unicodedata.normalize("NFC", "".join(_syllable(s) for s in numbered.split()))


def parse(text: str) -> pl.DataFrame:
    rows = []
    for line in text.splitlines():
        if line.startswith("#"):
            continue
        m = _LINE.match(line)
        if not m:
            continue
        trad, simp, numbered, defs = m.groups()
        glosas = [d for d in defs.split("/") if d]
        rows.append({"tradicional": trad, "palavra": simp, "pinyin": pinyin(numbered), "glosas": glosas})
    return pl.DataFrame(rows, schema={"tradicional": pl.String, "palavra": pl.String, "pinyin": pl.String, "glosas": pl.List(pl.String)})


def entries() -> pl.DataFrame:
    path = download(URL, max_age=MAX_AGE)
    with zipfile.ZipFile(path) as zf:
        name = next(n for n in zf.namelist() if n.endswith(".u8"))
        return parse(io.TextIOWrapper(zf.open(name), encoding="utf-8").read())


def real_glosses(glosas: list[str]) -> list[str]:
    return [g for g in glosas if not _META.match(g)]


def choose(readings: list[dict], translit: str | None) -> dict | None:
    """The reading a learner needs: the treebank's, else the one with most real
    definitions (lower-case pinyin first: capitalised readings are names)."""
    if not readings:
        return None
    # Same tones first ("ma" is the question particle 吗, "má" a colloquial
    # "what?"), then the same syllables ignoring tones, then any reading.
    matches = []
    if translit:
        t = unicodedata.normalize("NFC", translit.lower())
        matches = [r for r in readings if r["pinyin"].lower() == t] or [r for r in readings if fold(r["pinyin"]) == fold(t)]
    return max(matches or readings, key=lambda r: (len(real_glosses(r["glosas"])) > 0, r["pinyin"][:1].islower(), len(real_glosses(r["glosas"]))))
