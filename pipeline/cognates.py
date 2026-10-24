"""How alike two words of different languages are, and whether they are false friends.

Classes, from most to least useful to a learner:

* **igual** — same spelling once accents are dropped (es "casa", it "casa");
* **parecida** — one edit apart ("con"/"com"), or for longer words at least
  half the letters in place ("noche"/"noite", "Haus"/"house");
* **mesma origem** — looks different but Wiktionary gives both a common
  ancestor ("hijo" and "filho", both from Latin *filius*), or calls one a
  cognate of the other. Etymologies are incomplete, so this is a lower bound;
* **diferente**.

A **false friend** is a pair spelled the same in two languages whose English
definitions share no meaning: es "burro" (donkey) vs it "burro" (butter).
"""

from __future__ import annotations

import re

from .text import fold, levenshtein, similarity

CLASSES = ["igual", "parecida", "mesma origem", "diferente"]
SIMILAR = 0.5
MIN_LEN_SIMILAR = 4
# Ancestors this far back make almost every pair "related" (English "two" and
# Spanish "dos" share a Proto-Indo-European root), which tells a learner nothing.
REMOTE_ANCESTORS = ("ine-pro:",)

_PAREN = re.compile(r"\([^)]*(\)|$)|\[[^\]]*(\]|$)|“[^”]*(”|$)|\"[^\"]*(\"|$)")
_LEADING = re.compile(r"^(to|a|an|the|one's|oneself)\s+")


def gloss_heads(gloss: str, max_words: int = 3) -> set[str]:
    """Short translation-like pieces of an English gloss:
    "(formal) dog, hound" -> {"dog", "hound"}; "to eat; to have lunch" -> {"eat", "have lunch"}."""
    out = set()
    for part in re.split(r"[;,]", _PAREN.sub("", gloss)):
        head = _LEADING.sub("", part.strip().lower()).strip(" .!?:")
        if head and len(head.split()) <= max_words:
            out.add(head)
    return out


def looks_alike(a: str, b: str) -> bool:
    fa, fb = fold(a), fold(b)
    if min(len(fa), len(fb)) >= 2 and levenshtein(fa, fb) <= 1:
        return True
    return max(len(fa), len(fb)) >= MIN_LEN_SIMILAR and similarity(fa, fb) >= SIMILAR


def same_origin(a: tuple[str, str, set[str], set[str]], b: tuple[str, str, set[str], set[str]]) -> bool:
    """Each argument is (language, word, ancestor keys, cognate keys)."""
    lang_a, word_a, anc_a, cog_a = a
    lang_b, word_b, anc_b, cog_b = b
    near_a = {k for k in anc_a if not k.startswith(REMOTE_ANCESTORS)}
    near_b = {k for k in anc_b if not k.startswith(REMOTE_ANCESTORS)}
    if near_a & near_b:
        return True
    key_a, key_b = f"{lang_a}:{fold(word_a)}", f"{lang_b}:{fold(word_b)}"
    # One descends from the other, or Wiktionary names it as a cognate.
    return key_b in anc_a or key_a in anc_b or key_b in cog_a or key_a in cog_b


def classify(a: tuple[str, str, set[str], set[str]], b: tuple[str, str, set[str], set[str]]) -> tuple[str, float]:
    """(class, spelling similarity) of two words for the same concept."""
    wa, wb = a[1], b[1]
    sim = similarity(wa, wb)
    if fold(wa) == fold(wb):
        return "igual", 1.0
    if looks_alike(wa, wb):
        return "parecida", sim
    if same_origin(a, b):
        return "mesma origem", sim
    return "diferente", sim


def heads_overlap(a: set[str], b: set[str]) -> bool:
    """Shared meaning: a head in common, or one a prefix of the other ("photo" /
    "photograph"; at least four letters, so "car" doesn't match "care")."""
    if a & b:
        return True
    return any(len(x) >= 4 and len(y) >= 4 and (x.startswith(y) or y.startswith(x)) for x in a for y in b)


def false_friends(word: str, heads_a: set[str], heads_b: set[str], forma_de_a: set[str], forma_de_b: set[str], loans: set[str] | None = None) -> bool:
    """Same spelling, different meaning: no English gloss head in common; neither
    glossed by the word itself (Italian "okay": "okay!" is a loan, not a false
    friend); and not both inflections of look-alike words (es and it "visto"
    are both "seen", from "ver" and "vedere").

    ``loans`` are the heads checked for the word itself (default: both
    sides); English words list themselves as their meaning, so an English side
    is left out of it."""
    if not heads_a or not heads_b or heads_overlap(heads_a, heads_b):
        return False
    if fold(word) in {fold(h) for h in (heads_a | heads_b if loans is None else loans)}:
        return False
    return not any(looks_alike(x, y) for x in forma_de_a for y in forma_de_b)
