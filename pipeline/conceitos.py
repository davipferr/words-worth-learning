"""The same concept in six languages, and how much one language gives you of another.

A **concept** is one of the 5,000 most frequent English words (with its part
of speech). Its words in Spanish, French, Italian, German and Portuguese
come from that English entry's Wiktionary translation tables — but tables
are noisy ("dog" lists Spanish "vaca", a slang sense), so a word is accepted
only when it is common in its language (top 10,000 words; top 30,000
subtitle forms for Portuguese) and, preferably, when its *own* English
definitions name the concept back ("perro": "dog"). Concepts with no usable
table fall back to the reverse lookup: a common word whose first definition
is the concept.

The **advantage** of language A over language B is the share of everything
said in B (subtitle tokens) made of words that look like their equivalent in
A ("igual" or "parecida", see ``cognates``). Words of B with no aligned
concept count as not recognised, so the figure is a lower bound; the share
of B that could be aligned at all is reported next to it.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from itertools import combinations

from . import cognates
from .text import fold

ORIGENS = ["pt", "en", "es", "fr", "it", "de", "ja", "zh"]  # rows of the advantage matrix
ALVOS = ["en", "es", "fr", "it", "de", "ja", "zh"]  # columns: the languages the site teaches
RECONHECIVEL = {"igual", "parecida"}


@dataclass
class Word:
    """One word of a language's vocabulary, as the alignment needs it."""

    lang: str
    palavra: str
    rank: int
    share: float  # share of all subtitle tokens of the language
    pos: set[str] = field(default_factory=set)
    heads: set[str] = field(default_factory=set)  # English gloss heads, every sense
    first_head: str | None = None  # main head of the first definition
    first_heads: set[str] = field(default_factory=set)  # every head of the first definition
    forma_de: set[str] = field(default_factory=set)
    etimos: set[str] = field(default_factory=set)
    cognatos: set[str] = field(default_factory=set)
    glosas: list[str] = field(default_factory=list)
    roman: str | None = None  # Japanese romaji, Chinese toneless pinyin
    tradicional: str | None = None  # Chinese traditional spelling

    @property
    def key(self) -> tuple:
        return self.lang, self.palavra, self.etimos, self.cognatos, self.roman, self.tradicional


@dataclass
class Concept:
    conceito: str  # the English word
    classe: str  # its part of speech
    rank_en: int
    traducoes: list[str]  # "es:perro", table order (see wiktionary._translations)


def reverse_heads(vocab: dict[str, Word]) -> dict[tuple[str, str], Word]:
    """(first definition head, part of speech) -> the most frequent word with it."""
    out: dict[tuple[str, str], Word] = {}
    for w in sorted(vocab.values(), key=lambda w: w.rank):
        if w.first_head:
            for pos in w.pos:
                out.setdefault((w.first_head, pos), w)
    return out


def choose(concept: Concept, lang: str, vocab: dict[str, Word], reverse: dict[tuple[str, str], Word]) -> tuple[Word | None, bool]:
    """(word, confirmed) for a concept in one language.

    Among the table's candidates that are common in the language, the best
    is one whose first definition names the concept ("aller": "to go"), then
    one that names it in any definition ("faire" also has "to go", for
    sounds), the more frequent first. A candidate that never names the
    concept is used only if it is one of the table's top two.
    """
    target = concept.conceito.lower()
    cands = [t.split(":", 1)[1] for t in concept.traducoes if t.startswith(f"{lang}:")]
    scored = []
    for i, c in enumerate(cands):
        w = vocab.get(c.lower())
        if w is None:
            continue
        strength = 0 if target in w.first_heads else 1 if target in w.heads else 2
        if strength < 2 or i < 2:
            scored.append((strength, w.rank, w))
    if scored:
        strength, _, w = min(scored, key=lambda t: t[:2])
        return w, strength < 2
    w = reverse.get((target, concept.classe))
    return (w, True) if w else (None, False)


def align(concepts: list[Concept], vocabs: dict[str, dict[str, Word]]) -> list[dict]:
    """One row per concept: the chosen word, its rank and confirmation per language."""
    reverses = {lang: reverse_heads(v) for lang, v in vocabs.items() if lang != "en"}
    rows = []
    for c in concepts:
        row = {"conceito": c.conceito, "classe": c.classe, "rank_en": c.rank_en}
        en = vocabs["en"].get(c.conceito.lower())
        row["en"] = en
        for lang in (lang for lang in ORIGENS if lang in vocabs):
            if lang == "en":
                continue
            w, ok = choose(c, lang, vocabs[lang], reverses[lang])
            row[lang], row[f"ok_{lang}"] = w, ok
        rows.append(row)
    return rows


def pairs(aligned: list[dict]) -> list[dict]:
    """Every pair of languages for every concept, with class and similarity."""
    out = []
    for row in aligned:
        for a, b in combinations(ORIGENS, 2):
            wa, wb = row.get(a), row.get(b)
            if wa is None or wb is None:
                continue
            classe, sim = cognates.classify(wa.key, wb.key)
            out.append({"conceito": row["conceito"], "lingua_a": a, "palavra_a": wa.palavra, "lingua_b": b, "palavra_b": wb.palavra, "classe": classe, "similaridade": sim})
    return out


def advantage(aligned: list[dict], vocabs: dict[str, dict[str, Word]], top: int = 5000) -> list[dict]:
    """The advantage matrix: for each (A, B), the share of B's tokens that are
    recognisable from A, of same origin only, and aligned at all."""
    out = []
    for b in (b for b in ALVOS if b in vocabs):
        # For each word of B, the best class it reaches against each A, over
        # every concept where it is B's word.
        best: dict[str, dict[str, str]] = defaultdict(dict)
        partner: dict[str, dict[str, str]] = defaultdict(dict)
        for row in aligned:
            wb = row.get(b)
            if wb is None:
                continue
            for a in ORIGENS:
                if a == b or row.get(a) is None:
                    continue
                classe, _ = cognates.classify(row[a].key, wb.key)
                prev = best[a].get(wb.palavra)
                if prev is None or cognates.CLASSES.index(classe) < cognates.CLASSES.index(prev):
                    best[a][wb.palavra] = classe
                    partner[a][wb.palavra] = row[a].palavra
        # Unique words: Chinese vocabularies also index traditional spellings.
        words_b = list({w.palavra: w for w in vocabs[b].values() if w.rank <= top}.values())
        for a in (a for a in ORIGENS if a in vocabs):
            if a == b:
                continue
            share = {c: 0.0 for c in cognates.CLASSES}
            n = {c: 0 for c in cognates.CLASSES}
            n1000 = 0
            for w in words_b:
                c = best[a].get(w.palavra)
                if c:
                    share[c] += w.share
                    n[c] += 1
                    n1000 += c in RECONHECIVEL and w.rank <= 1000
            out.append(
                {
                    "origem": a,
                    "alvo": b,
                    "reconhecivel": share["igual"] + share["parecida"],
                    "igual": share["igual"],
                    "parecida": share["parecida"],
                    "mesma_origem": share["mesma origem"],
                    "alinhada": sum(share.values()),
                    "palavras_reconheciveis": n["igual"] + n["parecida"],
                    "reconheciveis_top1000": n1000,
                    "palavras_alinhadas": sum(n.values()),
                }
            )
    return out


def false_friend_pairs(vocabs: dict[str, dict[str, Word]], linked: set[tuple[str, str, str, str]], top: int = 5000) -> list[dict]:
    """Words spelled the same in two languages that mean different things.

    ``linked`` holds (lang_a, word_a, lang_b, word_b) pairs already joined by a
    concept, which are never false friends."""
    by_fold: dict[str, dict[str, Word]] = defaultdict(dict)
    for lang, vocab in vocabs.items():
        for w in {w.palavra: w for w in vocab.values()}.values():
            # Latin words need three letters to mean anything; Chinese and
            # Japanese words two characters (手紙: "letter" in Japanese,
            # "toilet paper" in Chinese). Chinese also by its traditional spelling.
            keys = {fold(w.palavra)} | ({fold(w.tradicional)} if w.tradicional else set())
            for f in keys:
                if w.rank <= top and len(f) >= (2 if lang in cognates.CJK else 3):
                    if lang not in by_fold[f] or w.rank < by_fold[f][lang].rank:
                        by_fold[f][lang] = w
    out = []
    for words in by_fold.values():
        for a, b in combinations([lang for lang in ORIGENS if lang in words], 2):
            wa, wb = words[a], words[b]
            if (a, wa.palavra, b, wb.palavra) in linked or (b, wb.palavra, a, wa.palavra) in linked:
                continue
            loans = (set() if a == "en" else wa.heads) | (set() if b == "en" else wb.heads)
            # Japanese and Chinese words with the same characters are usually
            # near-synonyms glossed differently (現場 "actual spot", 现场 "scene;
            # spot"): between them, any shared gloss word rules a pair out.
            if a in cognates.CJK and b in cognates.CJK and cognates.gloss_words(wa.glosas) & cognates.gloss_words(wb.glosas):
                continue
            if cognates.false_friends(wa.palavra, wa.heads, wb.heads, wa.forma_de, wb.forma_de, loans):
                out.append(
                    {
                        "lingua_a": a, "palavra_a": wa.palavra, "rank_a": wa.rank, "sentido_a": "; ".join(wa.glosas[:2]),
                        "lingua_b": b, "palavra_b": wb.palavra, "rank_b": wb.rank, "sentido_b": "; ".join(wb.glosas[:2]),
                    }
                )  # fmt: skip
    return sorted(out, key=lambda r: max(r["rank_a"], r["rank_b"]))
