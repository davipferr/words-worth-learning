"""Coverage curves: share of subtitle tokens covered by the top N words and forms."""

import polars as pl

from pipeline import frames
from pipeline.io import emit_parquet
from pipeline.langs import selected

emit_parquet(pl.concat([frames.cobertura(lang).with_columns(pl.lit(lang.code).alias("lingua")) for lang in selected()]).select("lingua", pl.exclude("lingua")))
