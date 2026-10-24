"""Words spelled the same in two languages that mean different things."""

from pipeline import frames
from pipeline.io import emit_parquet

emit_parquet(frames.falsos_amigos())
