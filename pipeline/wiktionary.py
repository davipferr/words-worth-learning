"""Wiktionary entries, as extracted by wiktextract (kaikki.org).

The English Wiktionary (``kaikki.org/dictionary/<Language>``) is by far the
largest: it links every inflected form to its lemma ("estoy" -> "estar") and
has part of speech, definitions (in English), pronunciation, gender and
etymology. Definitions are shown as Wiktionary writes them, untranslated.

Dumps are JSON Lines, one entry (word + part of speech + etymology) per line.
They are big (the English one is 530 MB gzipped), so each is parsed once into
a compact table, keeping only words that occur in the language's subtitles.
"""

from __future__ import annotations

import gzip
from collections.abc import Iterable, Iterator
from datetime import timedelta
from pathlib import Path
from urllib.parse import quote

import orjson
import polars as pl

from .http import download

# Senses with these tags are dropped when an entry has other senses: a learner
# wants "casa = house", not the 17th-century meaning.
MARGINAL = {"obsolete", "archaic", "dated", "rare", "historical", "nonstandard", "misspelling"}
GENEROS = {"masculine": "m", "feminine": "f", "neuter": "n"}
MAX_GLOSAS = 6
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


def compact(entry: dict) -> dict:
    """One English-Wiktionary entry -> the fields the pipeline uses."""
    lemma_senses, forma_de, generos = [], [], []
    for s in entry.get("senses") or []:
        targets = [f.get("word") for f in (s.get("form_of") or []) + (s.get("alt_of") or []) if f.get("word")]
        if targets:
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

    return {
        "palavra": entry.get("word"),
        "pos": entry.get("pos"),
        "glosas": glosas[:MAX_GLOSAS],
        "forma_de": forma_de[:6],
        "genero": "/".join(dict.fromkeys(generos)) or None,
        "ipa": _ipa(entry.get("sounds") or []),
        "etimo": etimo,
    }


def parse_en(lines: Iterable[bytes], keep: set[str] | None = None) -> pl.DataFrame:
    """Compact table of entries; ``keep`` (lower-cased words) filters before the
    expensive part, so only words that occur in subtitles are kept."""
    rows = []
    for line in lines:
        entry = orjson.loads(line)
        word = entry.get("word")
        if not word or (keep is not None and word.lower() not in keep):
            continue
        rows.append(compact(entry))
    return pl.DataFrame(rows, schema=SCHEMA)


def entries_en(language: str, keep: set[str] | None = None) -> pl.DataFrame:
    return parse_en(_lines(download(url_en(language), max_age=MAX_AGE)), keep)
