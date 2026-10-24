"""The advantage matrix: for each starting language and target language, the
share of the target's subtitle tokens recognisable from the starting one."""

from pipeline import frames
from pipeline.io import emit_parquet

emit_parquet(frames.vantagem())
