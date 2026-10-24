"""Every Anki deck (one .apkg per language and frequency band), as a zip that
Framework extracts on demand: pages link to ``data/decks/es-0001-0500.apkg``."""

import sys

from pipeline import anki, frames
from pipeline.langs import selected

decks = {}
for lang in selected():
    rows = anki.cards(frames.palavras(lang), frames.frases(lang)).to_dicts()
    for band in anki.BANDS:
        decks[anki.file_name(lang, band)] = anki.deck_bytes(rows, lang, band)
sys.stdout.buffer.write(anki.archive(decks))
sys.stdout.buffer.flush()
