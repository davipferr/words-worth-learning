"""From word forms to lemmas.

The frequency lists count *forms* ("estoy", "estaba", "estuvo"…); a learner
learns *lemmas* ("estar"). Form counts are summed into lemma counts:

1. contraction halves left by the tokenizer map to their word ("don" -> "do");
2. a form seen often enough in the language's Universal Dependencies treebank
   splits its count the way annotators lemmatised it there ("anda" -> "andar",
   "como" -> mostly the conjunction, a little "comer");
3. otherwise Wiktionary decides: a form that is a lemma itself (it has real
   definitions) counts for itself; a form that is only an inflection splits
   its count evenly between its lemmas ("fue" -> half "ser", half "ir");
4. proper nouns and tokens missing from Wiktionary are kept (they are part of
   what you hear) but never ranked as words to learn.
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass

import polars as pl

from .langs import Lang

TOP_FORMS = 50_000  # forms looked up in the dictionary (beyond that, each counts as itself)
UD_MIN = 3  # a form needs this many treebank occurrences for the treebank to decide
UD_MIN_SHARE = 0.05  # treebank lemmas below this share of a form are noise

STATUS = ["lema", "flexão", "contração", "nome próprio", "fora do dicionário"]


@dataclass
class Entry:
    palavra: str
    pos: str
    glosas: list[str]
    forma_de: list[str]
    genero: str | None
    ipa: str | None
    etimo: str | None

    @property
    def is_lemma(self) -> bool:
        return bool(self.glosas) and self.pos != "name"

    @property
    def is_letter(self) -> bool:
        """Entries for the letter or note itself ("de" = the letter D, "la" = the note A)."""
        # A noun entry with any letter sense is the letter's name ("mi": the
        # note E, and the Greek letter mu); other entries need all senses to be.
        letter = any if self.pos == "noun" else all
        return self.pos in LETTER_POS or letter(_LETTER_GLOSS.search(g) for g in self.glosas)


LETTER_POS = {"character", "symbol", "letter", "punct", "romanization", "suffix", "prefix", "infix", "interfix"}
_LETTER_GLOSS = re.compile(
    r"\bname of the\b.*\bletter\b|\bletter of the\b.*\balphabet\b|\b(greek|latin|cyrillic|hebrew|arabic) letter\b|\bsolf[eè]ge\b|\bnote\b.*\bscale\b", re.I
)


def index(dic: pl.DataFrame) -> dict[str, list[Entry]]:
    """Dictionary entries by lower-cased word, in dump order (Wiktionary's own order)."""
    idx: dict[str, list[Entry]] = defaultdict(list)
    for r in dic.iter_rows(named=True):
        idx[r["palavra"].lower()].append(Entry(**r))
    return idx


# Universal Dependencies part-of-speech tags -> Wiktionary's.
UPOS = {
    "NOUN": {"noun"}, "VERB": {"verb"}, "AUX": {"verb"}, "ADJ": {"adj"}, "ADV": {"adv"}, "PRON": {"pron"},
    "DET": {"det", "article", "pron"}, "ADP": {"prep", "contraction"}, "CCONJ": {"conj"}, "SCONJ": {"conj"},
    "NUM": {"num"}, "INTJ": {"intj"}, "PART": {"particle", "adv"},
}  # fmt: skip


def main_entries(entries: list[Entry], lemma: str, upos: str | None = None) -> list[Entry]:
    """A lemma's entries in the order a learner should see them: exact spelling;
    letter and affix entries last; the part of speech the treebank uses most
    for the lemma first ("mi" is "my" before it is the note E); otherwise
    Wiktionary's order (main etymology first)."""
    lemmas = [e for e in entries if e.is_lemma]
    exact = [e for e in lemmas if e.palavra == lemma] or lemmas
    wanted = UPOS.get(upos or "", set())
    return sorted(exact, key=lambda e: (e.is_letter, e.pos not in wanted))


def _lemma_word(entries: list[Entry], form: str) -> str:
    """Display spelling of a lemma: the exact spelling if it exists, else the
    dictionary's (German nouns are capitalised: "haus" -> "Haus")."""
    lemmas = [e for e in entries if e.is_lemma]
    for e in lemmas:
        if e.palavra == form:
            return form
    return lemmas[0].palavra


def _known(word: str, idx: dict[str, list[Entry]]) -> str | None:
    """Dictionary spelling of ``word`` if it is a lemma there."""
    entries = idx.get(word.lower(), [])
    return _lemma_word(entries, word) if any(e.is_lemma for e in entries) else None


def _treebank_lemma(lemma: str, upos: str, idx: dict[str, list[Entry]]) -> str | None:
    """Dictionary lemma for a treebank (lemma, part of speech) pair.

    Treebanks sometimes lemmatise to a word that Wiktionary lists, with that
    part of speech, only as a form of something else: AnCora's determiner
    "mi" is Wiktionary's apocope of "mío" (its own "mi" entries are the note
    and the Greek letter). Follow that link when no entry of the lemma has the
    treebank's part of speech.
    """
    word = _known(lemma, idx)
    entries = idx.get(lemma.lower(), [])
    wanted = UPOS.get(upos, set())
    if word and wanted and not any(e.is_lemma and not e.is_letter and e.pos in wanted for e in entries):
        for e in entries:
            if e.pos in wanted:
                for t in e.forma_de:
                    if target := _known(t, idx):
                        return target
    return word


def resolve(form: str, idx: dict[str, list[Entry]], lang: Lang, ud: dict[str, list[tuple[str, str, int]]] | None = None) -> tuple[str, list[tuple[str, float]]]:
    """(status, [(lemma, weight)]) for one lower-cased form; weights sum to 1."""
    if form in lang.contracoes:
        target = lang.contracoes[form]
        return "contração", [(_known(target, idx) or target, 1.0)]

    seen = (ud or {}).get(form, [])
    total = sum(n for *_, n in seen)
    if total >= UD_MIN:
        if sum(n for _, upos, n in seen if upos == "PROPN") > total / 2:
            return "nome próprio", [(form, 1.0)]
        weights: dict[str, float] = defaultdict(float)
        for lemma, upos, n in seen:
            if n / total >= UD_MIN_SHARE and upos != "PROPN" and (word := _treebank_lemma(lemma, upos, idx)):
                weights[word] += n
        if weights:
            s = sum(weights.values())
            status = "lema" if all(w.lower() == form for w in weights) else "flexão"
            return status, [(w, n / s) for w, n in sorted(weights.items(), key=lambda t: -t[1])]

    entries = idx.get(form, [])
    senses = sum(len(e.glosas) for e in entries if e.is_lemma and not e.is_letter)
    inflects = any(e.forma_de for e in entries if e.pos != "name")
    # A form that is also an inflection keeps its own entry only when that
    # entry is substantial: "flores" is the plural of "flor" far more often than
    # it is its single, obscure sense ("menstruation").
    if any(e.is_lemma for e in entries) and not (inflects and senses <= 1):
        return "lema", [(_lemma_word(entries, form), 1.0)]
    targets: list[str] = []
    for e in entries:
        if e.pos == "name":
            continue
        for t in e.forma_de:
            word = _known(t, idx)
            if word is None:
                # Form of a form ("dámelo" -> "da" -> "dar"): follow one more step.
                deeper = [u for x in idx.get(t.lower(), []) for u in x.forma_de if _known(u, idx)]
                word = _known(deeper[0], idx) if deeper else None
            if word and word not in targets:
                targets.append(word)
    if targets:
        return "flexão", [(t, 1 / len(targets)) for t in targets]
    if any(e.is_lemma for e in entries):
        return "lema", [(_lemma_word(entries, form), 1.0)]
    if entries:
        return "nome próprio", [(entries[0].palavra, 1.0)]
    return "fora do dicionário", [(form, 1.0)]


def ud_index(ud: pl.DataFrame) -> dict[str, list[tuple[str, str, int]]]:
    out: dict[str, list[tuple[str, str, int]]] = defaultdict(list)
    for forma, lema, upos, n in ud.select("forma", "lema", "upos", "n").iter_rows():
        out[forma].append((lema, upos, n))
    return out


def lemmatize(formas: pl.DataFrame, idx: dict[str, list[Entry]], lang: Lang, ud: pl.DataFrame | None = None, top: int = TOP_FORMS) -> pl.DataFrame:
    """One row per (form, lemma) with the share of the form's count it receives."""
    udx = ud_index(ud) if ud is not None else None
    rows = []
    for rank, (forma, contagem) in enumerate(formas.select("forma", "contagem").iter_rows(), 1):
        if rank <= top:
            status, lemmas = resolve(forma, idx, lang, udx)
        else:
            status, lemmas = "fora do dicionário", [(forma, 1.0)]
        for lema, peso in lemmas:
            rows.append((forma, rank, contagem, lema, peso, status))
    return pl.DataFrame(
        rows,
        schema={"forma": pl.String, "rank_forma": pl.Int64, "contagem": pl.Int64, "lema": pl.String, "peso": pl.Float64, "status": pl.String},
        orient="row",
    )
