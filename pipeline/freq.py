"""Word-form frequencies from OpenSubtitles (hermitdave/FrequencyWords, 2018 lists).

Each list is ``word count`` per line, lower-cased, counted over every subtitle
file of the language in OpenSubtitles 2018. Subtitles are the closest large,
open corpus to everyday speech, which is what a learner wants to understand.
The lists are frozen (the repository hasn't changed since 2018), so the
download is cached forever.

Japanese is the exception: its OpenSubtitles list was tokenized without
hiragana (no particles, verbs cut into kanji stems), so it comes from the
``wordfreq`` package instead, MeCab-segmented and blended from subtitles,
Wikipedia, news and social media. Its frequencies are proportions; they are
scaled to counts per billion words so the rest of the pipeline is unchanged.
"""

from __future__ import annotations

import polars as pl

from .http import download
from .text import is_cjk, is_word

BASE = "https://raw.githubusercontent.com/hermitdave/FrequencyWords/master/content/2018"
WORDFREQ = {"ja"}  # languages whose frequencies come from wordfreq
PER_BILLION = 1e9


def url(code: str) -> str:
    if code in WORDFREQ:
        return "https://github.com/rspeer/wordfreq"
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


def from_wordfreq(code: str) -> pl.DataFrame:
    import wordfreq

    freqs = wordfreq.get_frequency_dict(code, wordlist="best")
    lines = [f"{w} {round(f * PER_BILLION)}" for w, f in freqs.items() if " " not in w]
    return parse("\n".join(lines))


# Lists whose subtitles are often bilingual: Latin-script tokens there are
# English lines ("you", "the"), not Chinese or Japanese speech.
CJK_LISTS = {"ja", "zh_cn"}


def forms(code: str) -> pl.DataFrame:
    """Every word form with its count, most frequent first."""
    if code in WORDFREQ:
        df = from_wordfreq(code)
    else:
        df = parse(download(url(code), max_age=None).read_text(encoding="utf-8", errors="replace"))
    if code in CJK_LISTS:
        df = df.filter(pl.col("forma").map_elements(is_cjk, return_dtype=pl.Boolean))
    return df
