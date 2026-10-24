"""Choose example sentences a learner can actually read.

For each word, among the Tatoeba sentences that contain one of its forms, the
best example is one whose *other* words are all more common than the word
itself: if you study in frequency order, you already know everything else in
it (the "i+1" idea). Each sentence gets a difficulty — the rank of its rarest
other word — and the choice prefers, in order: a Portuguese translation, a
difficulty within reach, a comfortable length (around eight words).
Proper nouns ("Tom", Tatoeba's favourite character) count as known.
"""

from __future__ import annotations

import polars as pl

from .langs import Lang
from .text import tokenize

UNKNOWN = 1_000_000  # rank of a token that is not a learnable word
MIN_TOKENS, MAX_TOKENS, IDEAL_TOKENS = 3, 14, 8
PER_WORD = 3
# A sentence is "within reach" when its rarest other word ranks no worse than
# the word itself, or than this floor (everyone learns the first few hundred).
REACH_FLOOR = 300


def token_ranks(formas_lemas: pl.DataFrame, lemas: pl.DataFrame) -> pl.DataFrame:
    """Each form -> the rank of its best learnable lemma (and that lemma)."""
    ranked = lemas.select("lema", "rank", "tipo")
    fl = formas_lemas.select("forma", "lema").join(ranked, on="lema", how="left")
    return (
        fl.with_columns(
            pl.when(pl.col("rank").is_not_null()).then(pl.col("rank")).when(pl.col("tipo") == "nome próprio").then(0).otherwise(UNKNOWN).alias("r")
        )
        .sort("r")
        .group_by("forma")
        .agg(pl.col("r").first().alias("r"), pl.col("lema").first().alias("lema_r"))
    )


def choose(sentences: pl.DataFrame, formas_lemas: pl.DataFrame, lemas: pl.DataFrame, lang: Lang, top: int) -> pl.DataFrame:
    toks = (
        sentences.select("id", pl.col("texto").map_elements(lambda s: tokenize(s, lang.apostrofo), return_dtype=pl.List(pl.String)).alias("tok"))
        .with_columns(pl.col("tok").list.len().alias("n_tok"))
        .filter(pl.col("n_tok").is_between(MIN_TOKENS, MAX_TOKENS))
        .explode("tok")
        .rename({"tok": "forma"})
    )
    tr = token_ranks(formas_lemas, lemas)
    toks = toks.join(tr, on="forma", how="left").with_columns(pl.col("r").fill_null(UNKNOWN))

    # Rarest and second-rarest token per sentence: a word's difficulty in a
    # sentence is the rarest token that isn't the word itself.
    per_sent = (
        toks.sort("r", descending=True)
        .group_by("id")
        .agg(
            pl.col("n_tok").first(),
            pl.col("r").first().alias("r1"),
            pl.col("lema_r").first().alias("l1"),
            pl.col("r").slice(1, 1).first().fill_null(0).alias("r2"),
        )
    )

    words = lemas.filter(pl.col("rank") <= top).select("lema", "rank")
    pairs = (
        toks.select("id", "forma")
        .join(formas_lemas.select("forma", "lema"), on="forma")
        .join(words, on="lema")
        .unique(["id", "lema"], keep="first", maintain_order=True)
        .join(per_sent, on="id")
        .with_columns(pl.when(pl.col("lema") == pl.col("l1")).then(pl.col("r2")).otherwise(pl.col("r1")).alias("dificuldade"))
        .join(sentences, on="id")
        .with_columns(
            (pl.col("dificuldade") <= pl.max_horizontal(pl.col("rank"), pl.lit(REACH_FLOOR))).alias("ao_alcance"),
            (pl.col("n_tok") - IDEAL_TOKENS).abs().alias("dist_tam"),
        )
    )
    return (
        pairs.sort(
            [pl.col("trad_pt").is_null(), pl.col("ao_alcance").not_(), "dist_tam", "dificuldade", "id"],
        )
        .group_by("lema", maintain_order=True)
        .head(PER_WORD)
        .with_columns(pl.int_range(1, pl.len() + 1).over("lema").alias("ordem"))
        .select(
            "lema", "rank", "ordem", pl.col("id").alias("frase_id"), "texto", "forma",
            pl.coalesce("trad_pt", "trad_en").alias("traducao"),
            pl.when(pl.col("trad_pt").is_not_null()).then(pl.lit("pt")).otherwise(pl.lit("en")).alias("lingua_traducao"),
            pl.col("dificuldade").replace(UNKNOWN, None), "ao_alcance",
        )
        .sort("rank", "ordem")
    )  # fmt: skip
