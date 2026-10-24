"""The 5,000 most frequent words (lemmas) of each language, with their
definitions, forms, first example sentence and Anki note ID."""

import polars as pl

from pipeline import anki, frames
from pipeline.io import emit_parquet
from pipeline.langs import classe, selected

out = []
for lang in selected():
    c = anki.cards(frames.palavras(lang), frames.frases(lang))
    band = pl.Series("faixa", [next(f"{a}–{b}" for a, b in anki.BANDS if a <= r <= b) for r in c["rank"].to_list()])
    out.append(
        c.with_columns(
            pl.lit(lang.code).alias("lingua"),
            pl.col("classe").map_elements(classe, return_dtype=pl.String).alias("classe_pt"),
            pl.col("glosas").list.join(" · ").alias("definicao"),
            pl.col("formas").list.join(", ").alias("formas"),
            pl.col("lema").map_elements(lambda w, lang=lang: anki.guid(lang, w), return_dtype=pl.String).alias("guid"),
            band,
        ).select(
            "lingua", "rank", "lema", "classe", "classe_pt", "genero", "ipa", "definicao", "etimo",
            "contagem", "por_milhao", "cobertura", "n_formas", "formas",
            "frase", "forma", "traducao", "frase_id", "faixa", "guid",
        )  # fmt: skip
    )
emit_parquet(pl.concat(out))
