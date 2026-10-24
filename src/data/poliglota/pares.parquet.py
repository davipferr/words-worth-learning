"""Every pair of languages for every concept: the two words, their class
(igual, parecida, mesma origem, diferente) and spelling similarity."""

from pipeline import frames
from pipeline.io import emit_parquet

emit_parquet(frames.pares())
