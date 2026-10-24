"""Word-form frequencies from OpenSubtitles (hermitdave/FrequencyWords, 2018 lists).

Each list is ``word count`` per line, lower-cased, counted over every subtitle
file of the language in OpenSubtitles 2018. Subtitles are the closest large,
open corpus to everyday speech, which is what a learner wants to understand.
The lists are frozen (the repository hasn't changed since 2018), so the
download is cached forever.
"""

from __future__ import annotations

import polars as pl

from .http import download
from .text import is_word

BASE = "https://raw.githubusercontent.com/hermitdave/FrequencyWords/master/content/2018"


def url(code: str) -> str:
    return f"{BASE}/{code}/{code}_full.txt"


def parse(text: str) -> pl.DataFrame:
    """``word count`` lines -> (forma, contagem), letters-only tokens, merged
    after Unicode normalisation (the lists have a few duplicate spellings)."""
    formas, contagens = [], []
    for line in text.splitlines():
        word, _, count = line.rpartition(" ")
        if word and count.isdigit() and is_word(word):
            formas.append(word)
            contagens.append(int(count))
    return (
        pl.DataFrame({"forma": formas, "contagem": contagens}, schema={"forma": pl.String, "contagem": pl.Int64})
        .with_columns(pl.col("forma").str.normalize("NFC"))
        .group_by("forma")
        .agg(pl.col("contagem").sum())
        .sort(["contagem", "forma"], descending=[True, False])
    )


def forms(code: str) -> pl.DataFrame:
    """Every word form with its count, most frequent first."""
    path = download(url(code), max_age=None)
    return parse(path.read_text(encoding="utf-8", errors="replace"))
