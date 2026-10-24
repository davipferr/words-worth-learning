"""Wiktionary entries, as extracted by wiktextract (kaikki.org).

The English Wiktionary (``kaikki.org/dictionary/<Language>``) is by far the
largest: it links every inflected form to its lemma ("estoy" -> "estar") and
has part of speech, definitions (in English), pronunciation, gender and
etymology. Definitions are shown as Wiktionary writes them, untranslated.

For the Poliglota section two more fields link words across languages
without translating anything for the reader: English entries' translation
tables ("dog" -> es "perro", it "cane"…), which define the shared concepts,
and each entry's etymological ancestors and cognates (Latin *canis*), which
tell words of the same origin apart from look-alikes.

Dumps are JSON Lines, one entry (word + part of speech + etymology) per line.
They are big (the English one is 530 MB gzipped), so each is parsed once into
a compact table, keeping only words that occur in the language's subtitles.
"""

from __future__ import annotations

import gzip
import re
from collections.abc import Iterable, Iterator
from datetime import timedelta
from pathlib import Path
from urllib.parse import quote

import orjson
import polars as pl

from .http import download
from .text import fold

# Senses with these tags are dropped when an entry has other senses: a learner
# wants "casa = house", not the 17th-century meaning.
MARGINAL = {"obsolete", "archaic", "dated", "rare", "historical", "nonstandard", "misspelling"}
GENEROS = {"masculine": "m", "feminine": "f", "neuter": "n"}
CLIPPING = {"clipping", "abbreviation", "short-form", "ellipsis"}
MAX_GLOSAS = 6
# Languages whose translations are kept from English entries' tables, as
# {table code: our code}: tables list Mandarin as "cmn".
TRAD_LANGS = {"es": "es", "fr": "fr", "it": "it", "de": "de", "pt": "pt", "ja": "ja", "cmn": "zh"}
TRAD_PER_LANG = 4
# Etymology templates that name an ancestor: inherited, derived, borrowed…
ANCESTOR_TEMPLATES = {"inh", "inh+", "der", "der+", "bor", "bor+", "lbor", "ubor", "slbor", "obor", "uder", "cal", "lbor+"}
# kaikki.org re-extracts the dumps every few weeks; Wiktionary's entries for
# common words barely change, and the English dump is 530 MB.
MAX_AGE = timedelta(days=90)

SCHEMA = {
    "palavra": pl.String,
    "pos": pl.String,
    "glosas": pl.List(pl.String),
    "forma_de": pl.List(pl.String),
    "genero": pl.String,
    "ipa": pl.String,
    "etimo": pl.String,
    # "la:canis", "gem-pro:husa": ancestors named in the etymology, folded.
    "etimos": pl.List(pl.String),
    # "pt:cao": words Wiktionary calls cognates.
    "cognatos": pl.List(pl.String),
    # "es:perro": translations from the entry's tables (English entries only).
    "traducoes": pl.List(pl.String),
    # Japanese and Chinese: romanization without tone marks ("denwa", "dianhua"),
    # for comparing with Latin-script languages.
    "roman": pl.String,
    # Chinese: the traditional spelling (entries are keyed by it; ``palavra``
    # is the simplified one, as in mainland subtitles).
    "tradicional": pl.String,
    # Japanese: conjugated forms as MeCab segments them ("書き", "書い" for 書いた).
    "flexoes": pl.List(pl.String),
}


def url_en(language: str) -> str:
    return f"https://kaikki.org/dictionary/{quote(language)}/kaikki.org-dictionary-{quote(language)}.jsonl.gz"


def _lines(path: Path) -> Iterator[bytes]:
    opener = gzip.open if path.name.endswith(".gz") else open
    with opener(path, "rb") as fh:
        yield from fh


def _gloss(sense: dict) -> str | None:
    """The most specific gloss of a sense (wiktextract lists parent glosses first)."""
    glosses = sense.get("glosses") or []
    if not glosses:
        return None
    g = glosses[-1].strip().rstrip(":").strip()
    return g[:240] if g else None


def _ipa(sounds: list[dict]) -> str | None:
    """First phonemic transcription; for English, General American when tagged."""
    ipas = [s for s in sounds if s.get("ipa")]
    if not ipas:
        return None
    us = [s for s in ipas if {"US", "General-American"} & set(s.get("tags") or [])]
    phonemic = [s for s in (us or ipas) if s["ipa"].startswith("/")]
    return (phonemic or us or ipas)[0]["ipa"]


_PAREN = re.compile(r"\([^)]*\)")


def _key(lang: str, word: str) -> str:
    """"la", "*hūsą" -> "la:husa": comparable across entries."""
    return f"{lang}:{fold(word.strip().lstrip('*'))}"


def _etymology(entry: dict) -> tuple[list[str], list[str]]:
    ancestors: list[str] = []
    cognates: list[str] = []
    for t in entry.get("etymology_templates") or []:
        args = t.get("args") or {}
        name = t.get("name")
        if name in ANCESTOR_TEMPLATES and args.get("2") and args.get("3") and args["3"] != "-":
            ancestors.append(_key(args["2"], args["3"]))
        elif name in ("cog", "noncog") and args.get("1") and args.get("2"):
            cognates.append(_key(args["1"], args["2"]))
    return list(dict.fromkeys(ancestors))[:10], list(dict.fromkeys(cognates))[:16]


def _translations(entry: dict) -> list[str]:
    """Translations into ``TRAD_LANGS``, "lang:word", most senses first.

    Tables have one row per sense, in no reliable order (English "go" lists
    "dizer", to say, before "ir"); a word listed under many senses is the
    general translation ("ir" appears under most senses of "go").
    """
    senses: dict[tuple[str, str], set] = {}
    for t in [*(entry.get("translations") or []), *(t for s in entry.get("senses") or [] for t in s.get("translations") or [])]:
        lang = TRAD_LANGS.get(t.get("lang_code"))
        word = _PAREN.sub("", t.get("word") or "").strip()  # "(o) teu" -> "teu"
        if lang == "zh":
            if "Traditional-Chinese" in (t.get("tags") or []):
                continue
            word = word.split("/")[-1].strip()  # "電話 /电话": traditional / simplified
        if lang and word and " " not in word:
            senses.setdefault((lang, word), set()).add(t.get("sense"))
    out: list[str] = []
    for lang in TRAD_LANGS.values():
        ranked = sorted((w for (lg, w) in senses if lg == lang), key=lambda w: -len(senses[(lang, w)]))  # stable: ties keep table order
        out += [f"{lang}:{w}" for w in ranked[:TRAD_PER_LANG]]
    return out


_LATIN = re.compile(r"[A-Za-z]")
# Japanese inflected forms end in these before MeCab splits off the
# auxiliary: 書いた -> 書い + た, 書いて -> 書い + て, 書かない -> 書か + ない.
_JA_SUFFIXES = ("たら", "たり", "ない", "た", "だ", "て", "で")


def _roman(text: str | None) -> str | None:
    return fold(text).replace(" ", "").replace("-", "") if text else None


def _chinese(entry: dict) -> dict:
    """Simplified spelling and Mandarin pinyin of a Chinese entry."""
    simplified = next((f["form"] for f in entry.get("forms") or [] if "Simplified-Chinese" in (f.get("tags") or [])), None)
    pinyin = [s for s in entry.get("sounds") or [] if s.get("zh_pron") and {"Mandarin", "Pinyin"} <= set(s.get("tags") or [])]
    standard = [s for s in pinyin if "Standard" in (s.get("tags") or [])] or pinyin
    py = standard[0]["zh_pron"] if standard else None
    return {"palavra": simplified or entry.get("word"), "tradicional": entry.get("word"), "ipa": py, "roman": _roman(py)}


def _japanese(entry: dict) -> dict:
    """Kana reading, romaji and conjugated forms of a Japanese entry."""
    word = entry.get("word") or ""
    forms = entry.get("forms") or []
    romaji = next((f["form"] for f in forms if "romanization" in (f.get("tags") or [])), None)
    kana = next((s["other"] for s in entry.get("sounds") or [] if s.get("other")), None)
    reading = " · ".join(x for x in [kana if kana and kana != word else None, romaji] if x) or None
    flexoes: list[str] = []
    for f in forms:
        form = f.get("form") or ""
        if f.get("source") != "conjugation" and not {"stem", "past"} & set(f.get("tags") or []):
            continue
        if not form or _LATIN.search(form) or form == word:
            continue
        flexoes.append(form)
        for suffix in _JA_SUFFIXES:
            if form.endswith(suffix) and len(form) > len(suffix):
                flexoes.append(form[: -len(suffix)])
                break
    return {"ipa": reading, "roman": _roman(romaji), "flexoes": list(dict.fromkeys(flexoes))[:40]}


def compact(entry: dict, lang: str | None = None) -> dict:
    """One English-Wiktionary entry -> the fields the pipeline uses."""
    lemma_senses, forma_de, generos = [], [], []
    for s in entry.get("senses") or []:
        targets = [f.get("word") for f in (s.get("form_of") or []) + (s.get("alt_of") or []) if f.get("word")]
        # A clipping or abbreviation is a word of its own (テレビ, "TV", is
        # far more common than テレビジョン): keep it, with its gloss.
        if targets and not CLIPPING & set(s.get("tags") or []):
            forma_de += [t for t in targets if t not in forma_de]
            continue
        lemma_senses.append(s)
        generos += [GENEROS[t] for t in s.get("tags") or [] if t in GENEROS]
    main = [s for s in lemma_senses if not MARGINAL & set(s.get("tags") or [])] or lemma_senses
    glosas: list[str] = []
    for s in main:
        g = _gloss(s)
        if g and g not in glosas:
            glosas.append(g)
    generos += [GENEROS[t] for t in entry.get("tags") or [] if t in GENEROS]

    # First sentence of the etymology ("From Latin canis."), as written.
    etimo = (entry.get("etymology_text") or "").split(". ")[0].strip().rstrip(".")[:200] or None

    etimos, cognatos = _etymology(entry)
    extra = _chinese(entry) if lang == "zh" else _japanese(entry) if lang == "ja" else {}
    return {
        "palavra": entry.get("word"),
        "pos": entry.get("pos"),
        "glosas": glosas[:MAX_GLOSAS],
        "forma_de": forma_de[:6],
        "genero": "/".join(dict.fromkeys(generos)) or None,
        "ipa": _ipa(entry.get("sounds") or []),
        "etimo": etimo,
        "etimos": etimos,
        "cognatos": cognatos,
        "traducoes": _translations(entry),
        "roman": None,
        "tradicional": None,
        "flexoes": [],
    } | extra


def parse_en(lines: Iterable[bytes], keep: set[str] | None = None, lang: str | None = None) -> pl.DataFrame:
    """Compact table of entries; ``keep`` (lower-cased words) filters before the
    expensive part, so only words that occur in subtitles are kept. Chinese
    entries are keyed by their traditional spelling and Japanese verbs occur
    as conjugated forms, so for those the filter runs after ``compact``."""
    rows = []
    late = lang in ("zh", "ja")
    for line in lines:
        entry = orjson.loads(line)
        word = entry.get("word")
        if not word or (keep is not None and not late and word.lower() not in keep):
            continue
        row = compact(entry, lang)
        if keep is not None and late and row["palavra"].lower() not in keep and not any(f in keep for f in row["flexoes"]):
            continue
        rows.append(row)
    return pl.DataFrame(rows, schema=SCHEMA)


def entries_en(language: str, keep: set[str] | None = None, lang: str | None = None) -> pl.DataFrame:
    return parse_en(_lines(download(url_en(language), max_age=MAX_AGE)), keep, lang)
