"""Build-time data pipeline for the "words worth learning" site.

``freq``, ``wiktionary``, ``ud`` and ``tatoeba`` read the raw sources;
``lexicon`` turns word forms into lemmas; ``examples`` picks readable example
sentences; ``anki`` writes the decks; ``frames`` ties them together (memoised
as Parquet). The Observable Framework data loaders in ``src/data`` are thin
scripts that call into this package and write the result to stdout.
"""
