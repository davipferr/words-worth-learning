"""Example sentences and their translations from Tatoeba's weekly exports.

Tatoeba (tatoeba.org) is a crowd-sourced collection of sentences linked to
their translations, CC BY 2.0 FR. The per-language exports are small
(``spa_sentences.tsv.bz2`` is 6 MB) and the links files hold only the pairs
between two languages, so nothing needs the 200 MB global dump.
"""

from __future__ import annotations

import bz2
import io
from datetime import timedelta

import polars as pl

from .http import NotFound, download, log

BASE = "https://downloads.tatoeba.org/exports/per_language"
MAX_AGE = timedelta(days=30)


def sentences_url(lang3: str) -> str:
    return f"{BASE}/{lang3}/{lang3}_sentences.tsv.bz2"


def links_url(src: str, dst: str) -> str:
    return f"{BASE}/{src}/{src}-{dst}_links.tsv.bz2"


def _tsv(raw: bytes, columns: list[str], dtypes: list) -> pl.DataFrame:
    # Sentences may contain quote characters, so quoting is off; tabs never
    # occur inside a sentence.
    return pl.read_csv(
        io.BytesIO(bz2.decompress(raw)),
        separator="\t",
        has_header=False,
        new_columns=columns,
        schema_overrides=dict(zip(columns, dtypes)),
        quote_char=None,
        truncate_ragged_lines=True,
    )


def parse_sentences(raw: bytes) -> pl.DataFrame:
    return _tsv(raw, ["id", "lingua", "texto"], [pl.Int64, pl.String, pl.String]).select("id", "texto").drop_nulls()


def parse_links(raw: bytes) -> pl.DataFrame:
    return _tsv(raw, ["id", "trad_id"], [pl.Int64, pl.Int64])


def sentences(lang3: str) -> pl.DataFrame:
    return parse_sentences(download(sentences_url(lang3), max_age=MAX_AGE).read_bytes())


def links(src: str, dst: str) -> pl.DataFrame:
    try:
        return parse_links(download(links_url(src, dst), max_age=MAX_AGE).read_bytes())
    except NotFound:
        log(f"tatoeba: no {src}-{dst} links file")
        return pl.DataFrame(schema={"id": pl.Int64, "trad_id": pl.Int64})


def translated(src: pl.DataFrame, links_: pl.DataFrame, dst: pl.DataFrame, name: str) -> pl.DataFrame:
    """For each source sentence, its shortest linked translation (column ``name``)."""
    return (
        links_.join(dst.rename({"id": "trad_id", "texto": name}), on="trad_id")
        .sort(pl.col(name).str.len_chars())
        .group_by("id", maintain_order=True)
        .first()
        .select("id", name)
        .join(src.select("id"), on="id", how="semi")
    )


def with_translations(lang3: str, pt: pl.DataFrame, en: pl.DataFrame | None) -> pl.DataFrame:
    """Sentences of ``lang3`` that have a Portuguese or (fallback) English translation.

    ``pt``/``en`` are the Portuguese and English sentence tables; ``en`` is None
    when the target language is English itself.
    """
    src = sentences(lang3)
    out = src.join(translated(src, links(lang3, "por"), pt, "trad_pt"), on="id", how="left")
    if en is not None:
        out = out.join(translated(src, links(lang3, "eng"), en, "trad_en"), on="id", how="left")
    else:
        out = out.with_columns(pl.lit(None, pl.String).alias("trad_en"))
    return out.filter(pl.col("trad_pt").is_not_null() | pl.col("trad_en").is_not_null())
