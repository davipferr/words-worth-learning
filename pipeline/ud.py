"""Which lemma a form usually stands for, from Universal Dependencies treebanks.

Wiktionary says *what* a form can be ("anda" is a form of "andar", and also
a noun meaning a litter), not *how often* it is each one. UD treebanks are
hand-annotated corpora where every token carries its lemma, so counting
(form, lemma) pairs gives P(lemma | form): "anda" is "andar" almost always,
"como" is the conjunction/adverb far more often than "I eat".

Files are CoNLL-U: one token per line, ``ID FORM LEMMA UPOS …``; multi-word
tokens ("del" = "de" + "el") have a range ID and are skipped (their parts are
counted, and Wiktionary covers the contraction itself).
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from datetime import timedelta

import polars as pl

from .http import download

BASE = "https://raw.githubusercontent.com/UniversalDependencies"
SPLITS = ("train", "dev", "test")
MAX_AGE = timedelta(days=180)  # treebanks are released twice a year


def urls(treebank: str) -> list[str]:
    """``UD_Spanish-AnCora/es_ancora`` -> the train/dev/test CoNLL-U URLs."""
    repo, prefix = treebank.split("/")
    return [f"{BASE}/{repo}/master/{prefix}-ud-{s}.conllu" for s in SPLITS]


def parse(lines: Iterable[str]) -> Counter:
    """Counter of (lower-cased form, lemma, upos)."""
    counts: Counter = Counter()
    for line in lines:
        if not line or line[0] == "#" or line[0] == "\n":
            continue
        cols = line.rstrip("\n").split("\t")
        if len(cols) < 4 or not cols[0].isdigit():
            continue  # multi-word token ranges ("3-4") and empty nodes ("8.1")
        form, lemma, upos = cols[1].lower(), cols[2], cols[3]
        if lemma and lemma != "_" and upos != "PUNCT":
            counts[(form, lemma, upos)] += 1
    return counts


def lemma_counts(treebank: str) -> pl.DataFrame:
    counts: Counter = Counter()
    for url in urls(treebank):
        with download(url, max_age=MAX_AGE).open(encoding="utf-8") as fh:
            counts.update(parse(fh))
    return pl.DataFrame(
        [(f, l, u, n) for (f, l, u), n in counts.items()],
        schema={"forma": pl.String, "lema": pl.String, "upos": pl.String, "n": pl.Int64},
        orient="row",
    )


def parse_translit(lines: Iterable[str]) -> Counter:
    """Counter of (lemma, lemma transliteration) from the MISC column
    (``LTranslit=shuō``), which the Chinese treebank fills with pinyin."""
    counts: Counter = Counter()
    for line in lines:
        if not line or line[0] in "#\n":
            continue
        cols = line.rstrip("\n").split("\t")
        if len(cols) < 10 or not cols[0].isdigit():
            continue
        for item in cols[9].split("|"):
            if item.startswith("LTranslit="):
                counts[(cols[2], item.split("=", 1)[1])] += 1
    return counts


def lemma_translit(treebank: str) -> dict[str, str]:
    """Most frequent transliteration of each lemma."""
    counts: Counter = Counter()
    for url in urls(treebank):
        with download(url, max_age=MAX_AGE).open(encoding="utf-8") as fh:
            counts.update(parse_translit(fh))
    best: dict[str, tuple[int, str]] = {}
    for (lemma, translit), n in counts.items():
        if lemma not in best or n > best[lemma][0]:
            best[lemma] = (n, translit)
    return {lemma: t for lemma, (_, t) in best.items()}
