"""The 5,000 most frequent English words as concepts, with their word in
Portuguese, Spanish, French, Italian and German and how much each looks like
the Portuguese one."""

import polars as pl

from pipeline import frames
from pipeline.io import emit_parquet
from pipeline.langs import classe

emit_parquet(frames.conceitos_lado_a_lado().with_columns(pl.col("classe").map_elements(classe, return_dtype=pl.String).alias("classe_pt")))
