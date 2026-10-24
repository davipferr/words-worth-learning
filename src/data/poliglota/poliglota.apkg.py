"""Multilingual Anki deck: one note per concept, five languages on the back."""

import sys

from pipeline import anki, frames

sys.stdout.buffer.write(anki.poliglota_deck_bytes(frames.conceitos_lado_a_lado().to_dicts()))
sys.stdout.buffer.flush()
