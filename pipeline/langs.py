"""The languages the site covers and what each source calls them.

The site is in Portuguese and example sentences come with their Portuguese
translation when Tatoeba has one. ``WWL_LANGS`` picks which target languages
a build includes (default: all of them).
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Lang:
    code: str  # ISO 639-1, also FrequencyWords' folder name
    nome: str  # Portuguese name, shown on the site
    kaikki: str  # English Wiktionary's language name (kaikki.org/dictionary/<name>)
    tatoeba: str  # ISO 639-3, Tatoeba's per-language export folder
    tts: str  # Anki's {{tts}} voice locale
    ud: str = ""  # Universal Dependencies treebank, "UD_<Repo>/<file prefix>"
    # How the tokenizer splits apostrophes, matching the OpenSubtitles lists:
    # English keeps the apostrophe on the right ("don" + "'t"), French and
    # Italian on the left ("c'" + "est").
    apostrofo: str = "none"  # "right" | "left" | "none"
    # Tokens that are halves of contractions, mapped to the word they stand for.
    # The frequency lists split "don't" into "don" and "'t"; without this,
    # "don" would be counted as the verb "to don".
    contracoes: dict[str, str] = field(default_factory=dict)


LANGS: dict[str, Lang] = {
    "en": Lang(
        "en", "Inglês", "English", "eng", "en_US", ud="UD_English-EWT/en_ewt", apostrofo="right",
        contracoes={
            "don": "do", "doesn": "do", "didn": "do", "won": "will", "isn": "be", "aren": "be",
            "wasn": "be", "weren": "be", "ain": "be", "couldn": "could", "shouldn": "should",
            "wouldn": "would", "haven": "have", "hasn": "have", "hadn": "have", "mustn": "must",
            "needn": "need", "'t": "not", "'m": "be", "'re": "be", "'ll": "will", "'ve": "have", "'d": "would",
        },
    ),  # fmt: skip
    "es": Lang("es", "Espanhol", "Spanish", "spa", "es_ES", ud="UD_Spanish-AnCora/es_ancora"),
    "fr": Lang(
        "fr", "Francês", "French", "fra", "fr_FR", ud="UD_French-GSD/fr_gsd", apostrofo="left",
        contracoes={
            "c'": "ce", "l'": "le", "j'": "je", "d'": "de", "qu'": "que", "n'": "ne",
            "s'": "se", "m'": "me", "t'": "te", "jusqu'": "jusque", "lorsqu'": "lorsque", "puisqu'": "puisque",
        },
    ),  # fmt: skip
    "it": Lang(
        "it", "Italiano", "Italian", "ita", "it_IT", ud="UD_Italian-ISDT/it_isdt", apostrofo="left",
        contracoes={
            "l'": "lo", "un'": "uno", "dell'": "dello", "all'": "allo", "dall'": "dallo", "nell'": "nello",
            "sull'": "sullo", "c'": "ci", "d'": "di", "m'": "mi", "t'": "ti", "s'": "si", "quest'": "questo",
            "quell'": "quello", "po'": "poco", "com'": "come", "dov'": "dove", "cos'": "cosa",
        },
    ),  # fmt: skip
    "de": Lang("de", "Alemão", "German", "deu", "de_DE", ud="UD_German-GSD/de_gsd"),
}

# Wiktionary's part-of-speech codes, in Portuguese.
CLASSES = {
    "noun": "substantivo", "verb": "verbo", "adj": "adjetivo", "adv": "advérbio", "pron": "pronome",
    "det": "determinante", "article": "artigo", "prep": "preposição", "conj": "conjunção", "intj": "interjeição",
    "num": "numeral", "particle": "partícula", "contraction": "contração", "phrase": "expressão",
    "prep_phrase": "locução", "adv_phrase": "locução", "postp": "posposição",
}  # fmt: skip
GENEROS = {"m": "masculino", "f": "feminino", "n": "neutro", "m/f": "masculino ou feminino", "f/m": "masculino ou feminino"}


def classe(pos: str | None) -> str:
    return CLASSES.get(pos or "", "outra")


# The reader's language, for Tatoeba's sentence translations.
PT = Lang("pt", "Português", "Portuguese", "por", "pt_BR")


def selected() -> list[Lang]:
    """Target languages for this build, in the order given by ``WWL_LANGS``."""
    codes = [c.strip() for c in os.environ.get("WWL_LANGS", ",".join(LANGS)).split(",") if c.strip()]
    unknown = [c for c in codes if c not in LANGS]
    if unknown:
        raise SystemExit(f"WWL_LANGS: unknown language(s) {unknown}; choose from {list(LANGS)}")
    return [LANGS[c] for c in codes]
