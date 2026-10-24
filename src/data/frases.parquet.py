"""Up to three Tatoeba example sentences per word, easiest first."""

import polars as pl

from pipeline import frames
from pipeline.io import emit_parquet
from pipeline.langs import selected

emit_parquet(pl.concat([frames.frases(lang).with_columns(pl.lit(lang.code).alias("lingua")) for lang in selected()]).select("lingua", pl.exclude("lingua")))
