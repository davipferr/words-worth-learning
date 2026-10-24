"""Cleaned, shared frames, memoised as Parquet in the cache directory.

Downloads are cached by ``http``; this layer caches the parsed and derived
tables so several loaders (which run as separate processes) share them.

File names carry a hash of the code that builds them: the heavy parses of the
raw dumps depend only on their own module (editing the cognate rules must not
re-parse the 530 MB English Wiktionary), derived frames on the whole package.
"""

from __future__ import annotations

import hashlib
import time
from collections.abc import Callable
from datetime import timedelta
from pathlib import Path

import polars as pl

from . import cedict, cognates, conceitos, examples, freq, lexicon, tatoeba, ud, wiktionary
from .text import fold, is_cjk
from .http import CACHE_DIR, log
from .langs import LANGS, PT, Lang
from .schema import require_columns

FRAMES = CACHE_DIR / "frames"
PKG = Path(__file__).parent

# Learnable lemmas with a coverage curve; the site lists the first
# ``TOP_WORDS`` of them.
TOP_LEMMAS = 10_000
TOP_WORDS = 5_000


def code_version(*modules: str) -> str:
    """Short hash of the given modules of this package (all of them by default),
    line endings normalised so a Windows checkout and CI agree."""
    files = [PKG / f"{m}.py" for m in modules] if modules else sorted(PKG.glob("*.py"))
    h = hashlib.sha256()
    for src in files:
        h.update(src.name.encode())
        h.update(src.read_bytes().replace(b"\r\n", b"\n"))
    return h.hexdigest()[:12]


CODE_VERSION = code_version()


def memo(name: str, build: Callable[[], pl.DataFrame], *, deps: tuple[str, ...] = (), max_age: timedelta = timedelta(days=1)) -> pl.DataFrame:
    path = FRAMES / f"{name}-{code_version(*deps)}.parquet"
    if path.exists() and time.time() - path.stat().st_mtime < max_age.total_seconds():
        return pl.read_parquet(path)
    t0 = time.time()
    df = build()
    FRAMES.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".parquet.part")
    df.write_parquet(tmp)
    tmp.replace(path)
    # Drop copies built by other code versions.
    for old in FRAMES.glob(f"{name}-*.parquet"):
        if old != path:
            old.unlink(missing_ok=True)
    log(f"frame {name}: {df.height:,} rows in {time.time() - t0:.1f}s")
    return df


RAW_AGE = timedelta(days=30)

# ---------------------------------------------------------------- raw parses


def formas(code: str) -> pl.DataFrame:
    """Every word form of a language's subtitles with its count."""
    return memo(f"formas-{code}", lambda: require_columns(freq.forms(code), ["forma", "contagem"], f"FrequencyWords {code}", min_rows=10_000), deps=("freq", "text"), max_age=RAW_AGE)


def dicionario(lang: Lang) -> pl.DataFrame:
    """English-Wiktionary entries of the language, for words that occur in its subtitles."""

    def build() -> pl.DataFrame:
        keep = set(formas(lang.freq_code)["forma"].to_list()) | set(lang.contracoes.values())
        log(f"parsing Wiktionary ({lang.kaikki}) for {len(keep):,} subtitle forms")
        dic = require_columns(wiktionary.entries_en(lang.kaikki, keep, lang.code), ["palavra", "pos", "glosas", "forma_de"], f"kaikki {lang.kaikki}", min_rows=5_000)
        if lang.code == "zh":
            # Words CC-CEDICT has and Wiktionary doesn't (common compounds,
            # colloquialisms) become lemmas too; part of speech "cedict".
            cd = cedict_tabela().filter(pl.col("palavra").is_in(list(keep)), ~pl.col("palavra").is_in(dic["palavra"].implode()))
            extra = cd.group_by("palavra", maintain_order=True).agg(pl.col("glosas").first(), pl.col("pinyin").first(), pl.col("tradicional").first())
            dic = pl.concat([dic, extra.select(
                "palavra", pl.lit("cedict").alias("pos"), "glosas", pl.lit([], pl.List(pl.String)).alias("forma_de"),
                pl.lit(None, pl.String).alias("genero"), pl.col("pinyin").alias("ipa"), pl.lit(None, pl.String).alias("etimo"),
                *[pl.lit([], pl.List(pl.String)).alias(c) for c in ("etimos", "cognatos", "traducoes")],
                pl.col("pinyin").map_elements(lambda p: fold(p).replace(" ", ""), return_dtype=pl.String).alias("roman"),
                "tradicional", pl.lit([], pl.List(pl.String)).alias("flexoes"),
            )])  # fmt: skip
        return dic

    return memo(f"dic-{lang.code}", build, deps=("wiktionary", "freq", "text", "langs", "cedict"), max_age=RAW_AGE)


def cedict_tabela() -> pl.DataFrame:
    """CC-CEDICT: one row per (word, reading)."""
    return memo("cedict", cedict.entries, deps=("cedict",), max_age=RAW_AGE)


# Treebank part of speech -> the class shown for Chinese words, whose
# Wiktionary entries are per character ("character") or absent ("cedict").
UPOS_CLASSE = {
    "NOUN": "noun", "VERB": "verb", "AUX": "verb", "ADJ": "adj", "ADV": "adv", "PRON": "pron", "DET": "det",
    "ADP": "prep", "CCONJ": "conj", "SCONJ": "conj", "NUM": "num", "PART": "particle", "INTJ": "intj",
}  # fmt: skip


def frases_pt() -> pl.DataFrame:
    return memo("tatoeba-por", lambda: tatoeba.sentences(PT.tatoeba), deps=("tatoeba",), max_age=RAW_AGE)


def frases_en() -> pl.DataFrame:
    return memo("tatoeba-eng", lambda: tatoeba.sentences("eng"), deps=("tatoeba",), max_age=RAW_AGE)


def frases_traduzidas(lang: Lang) -> pl.DataFrame:
    """Tatoeba sentences of the language with a Portuguese or English translation."""
    return memo(
        f"tatoeba-traduzidas-{lang.code}",
        lambda: tatoeba.with_translations(lang.tatoeba, frases_pt(), None if lang.code == "en" else frases_en()),
        deps=("tatoeba",),
        max_age=RAW_AGE,
    )


# ------------------------------------------------------------------- derived


def treebank(lang: Lang) -> pl.DataFrame:
    """(form, lemma, upos) counts from the language's UD treebank."""
    return memo(f"ud-{lang.code}", lambda: require_columns(ud.lemma_counts(lang.ud), ["forma", "lema", "n"], f"UD {lang.ud}", min_rows=5_000), deps=("ud",), max_age=RAW_AGE)


def formas_lemas(lang: Lang) -> pl.DataFrame:
    """Each form of the language with the lemma(s) it counts for."""
    return memo(
        f"formas-lemas-{lang.code}",
        lambda: lexicon.lemmatize(formas(lang.freq_code), lexicon.index(dicionario(lang)), lang, treebank(lang) if lang.ud_lemas else None),
    )


def upos_by_lemma(lang: Lang) -> dict[str, str]:
    """The part of speech each lemma has most often in the language's treebank."""
    tb = treebank(lang).filter(pl.col("upos") != "PROPN").group_by("lema", "upos").agg(pl.col("n").sum()).sort("n", descending=True)
    out: dict[str, str] = {}
    for lema, upos in tb.select("lema", "upos").iter_rows():
        out.setdefault(lema.lower(), upos)
    return out


def lemas(lang: Lang) -> pl.DataFrame:
    """Every lemma heard in the language's subtitles with its count; learnable
    lemmas (words with a Wiktionary definition) are ranked and described."""

    def build() -> pl.DataFrame:
        total = total_tokens(lang)
        idx = lexicon.index(dicionario(lang))
        agg = (
            formas_lemas(lang)
            .with_columns((pl.col("contagem") * pl.col("peso")).alias("c"))
            .sort("c", descending=True)
            .group_by("lema")
            .agg(
                pl.col("c").sum().alias("contagem"),
                pl.len().alias("n_formas"),
                pl.col("forma").head(6).alias("formas"),
                pl.col("status").first().alias("status_forma"),
            )
        )
        # Chinese and Japanese lists keep only words in their own scripts.
        learnable = [any(e.is_lemma for e in idx.get(w.lower(), [])) and (not lang.cjk or is_cjk(w)) for w in agg["lema"].to_list()]
        agg = agg.with_columns(pl.Series("aprendivel", learnable, pl.Boolean)).with_columns(
            pl.when(pl.col("aprendivel"))
            .then(pl.lit("palavra"))
            .when(pl.col("status_forma") == "nome próprio")
            .then(pl.lit("nome próprio"))
            .otherwise(pl.lit("fora do dicionário"))
            .alias("tipo")
        )
        words = (
            agg.filter(pl.col("aprendivel"))
            .sort(["contagem", "lema"], descending=[True, False])
            .with_row_index("rank", offset=1)
            .with_columns((pl.col("contagem") / total * 1e6).alias("por_milhao"), (pl.col("contagem").cum_sum() / total).alias("cobertura"))
        )

        upos = upos_by_lemma(lang)
        if lang.code == "zh":
            readings: dict[str, list[dict]] = {}
            for r in cedict_tabela().iter_rows(named=True):
                readings.setdefault(r["palavra"], []).append(r)
            translit = ud.lemma_translit(lang.ud)
        info = []
        for lema, rank in words.select("lema", "rank").iter_rows():
            if rank > TOP_LEMMAS:
                break
            every = idx[lema.lower()]
            main = lexicon.main_entries(every, lema, upos.get(lema.lower()))
            glosas: list[str] = []
            # Letter and syllable entries only when there is nothing else (て is
            # a particle, not "the hiragana syllable て").
            for e in [e for e in main if not e.is_letter] or main:
                for g in e.glosas:
                    if len(glosas) < 4 and g not in glosas:
                        glosas.append(g)
            row = {
                "lema": lema,
                "classe": main[0].pos,
                "classes": list(dict.fromkeys(e.pos for e in main)),
                "genero": main[0].genero if main[0].pos == "noun" else None,
                "ipa": next((e.ipa for e in main if e.ipa), None) or next((e.ipa for e in every if e.ipa), None),
                "etimo": next((e.etimo for e in main if e.etimo), None),
                "glosas": glosas,
            }
            if lang.code == "zh":
                # Definitions and pinyin from CC-CEDICT, for the reading the
                # treebank uses; the class from the treebank when Wiktionary
                # only has a per-character entry.
                pick = cedict.choose(readings.get(lema, []), translit.get(lema))
                if pick:
                    row["glosas"] = (cedict.real_glosses(pick["glosas"]) or pick["glosas"])[:4]
                    row["ipa"] = pick["pinyin"]
                if row["classe"] in ("character", "cedict") and upos.get(lema.lower()) in UPOS_CLASSE:
                    row["classe"] = UPOS_CLASSE[upos[lema.lower()]]
            info.append(row)
        schema = {"lema": pl.String, "classe": pl.String, "classes": pl.List(pl.String), "genero": pl.String, "ipa": pl.String, "etimo": pl.String, "glosas": pl.List(pl.String)}
        words = words.join(pl.DataFrame(info, schema=schema), on="lema", how="left")
        others = agg.filter(~pl.col("aprendivel"))
        return (
            pl.concat([words, others], how="diagonal_relaxed")
            .drop("aprendivel", "status_forma")
            .sort(["rank", "contagem"], descending=[False, True], nulls_last=True)
        )

    return memo(f"lemas-{lang.code}", build)


def palavras(lang: Lang) -> pl.DataFrame:
    """The ``TOP_WORDS`` learnable lemmas, ranked."""
    return lemas(lang).filter(pl.col("rank") <= TOP_WORDS)


def frases(lang: Lang) -> pl.DataFrame:
    """Up to three example sentences per listed word."""
    return memo(f"frases-{lang.code}", lambda: examples.choose(frases_traduzidas(lang), formas_lemas(lang), lemas(lang), lang, top=TOP_WORDS))


def cobertura(lang: Lang) -> pl.DataFrame:
    """Share of all subtitle tokens covered by the top N words (lemmas) and,
    for comparison, by the top N forms learned one by one."""

    def build() -> pl.DataFrame:
        total = total_tokens(lang)
        w = lemas(lang).filter(pl.col("rank") <= TOP_LEMMAS).select("rank", "cobertura")
        f = formas(lang.freq_code).head(TOP_LEMMAS).select(
            pl.int_range(1, pl.len() + 1).alias("rank"), (pl.col("contagem").cum_sum() / total).alias("cobertura_formas")
        )
        return w.join(f, on="rank", how="left").sort("rank")

    return memo(f"cobertura-{lang.code}", build)


def total_tokens(lang: Lang) -> int:
    return int(formas(lang.freq_code)["contagem"].sum())


# ----------------------------------------------------------------- poliglota

VOCAB_TOP = 10_000  # words of each language eligible for alignment
PT_TOP_FORMS = 30_000  # Portuguese has no lemma ranking: its most frequent subtitle forms

VOCAB_SCHEMA = {
    "palavra": pl.String, "rank": pl.Int64, "share": pl.Float64, "pos": pl.List(pl.String), "heads": pl.List(pl.String),
    "first_head": pl.String, "first_heads": pl.List(pl.String), "forma_de": pl.List(pl.String), "etimos": pl.List(pl.String), "cognatos": pl.List(pl.String),
    "glosas": pl.List(pl.String), "traducoes": pl.List(pl.String), "roman": pl.String, "tradicional": pl.String,
}  # fmt: skip


def _vocab_row(palavra: str, rank: int, share: float, every: list, main: list, english: bool = False) -> dict:
    lemma_entries = [e for e in every if e.is_lemma]
    heads = {h for e in lemma_entries for g in e.glosas for h in cognates.gloss_heads(g)}
    if english:
        # English entries are defined in full sentences ("A wheeled vehicle…"),
        # not glossed; the word itself is its meaning in English.
        heads.add(palavra.lower())
    glosas = [g for e in main for g in e.glosas]
    first = cognates.gloss_heads(glosas[0]) if glosas else set()
    return {
        "palavra": palavra,
        "rank": rank,
        "share": share,
        "pos": sorted({e.pos for e in main}),
        "heads": sorted(heads),
        # The first definition's first piece: "perro" -> "dog".
        "first_head": next(iter(sorted(first, key=lambda h: glosas[0].lower().find(h))), None) if first else None,
        "first_heads": sorted(first),
        "forma_de": sorted({t for e in every for t in e.forma_de}),
        "etimos": list(dict.fromkeys(k for e in every for k in e.etimos)),
        "cognatos": list(dict.fromkeys(k for e in every for k in e.cognatos)),
        "glosas": glosas[:4],
        # Only the main part of speech: "will" the modal verb has no table,
        # and its noun's ("arbítrio") would be wrong.
        "traducoes": list(dict.fromkeys(t for e in main if e.pos == main[0].pos for t in e.traducoes)),
        "roman": next((e.roman for e in main if e.roman), None),
        "tradicional": next((e.tradicional for e in main if e.tradicional), None),
    }


def vocabulario(lang: Lang) -> pl.DataFrame:
    """The words of a language eligible for the Poliglota alignment, with
    what alignment needs: English gloss heads, ancestors, cognates, translations."""

    def build() -> pl.DataFrame:
        idx = lexicon.index(dicionario(lang))
        rows = []
        if lang.code == "pt":
            fm = formas(lang.freq_code)
            total = fm["contagem"].sum()
            for rank, (forma, contagem) in enumerate(fm.head(PT_TOP_FORMS).iter_rows(), 1):
                every = idx.get(forma, [])
                main = lexicon.main_entries(every, forma)
                if main and not main[0].is_letter:
                    rows.append(_vocab_row(lexicon._lemma_word(every, forma), rank, contagem / total, every, main))
        else:
            total = total_tokens(lang)
            upos = upos_by_lemma(lang)
            for lema, rank, contagem in lemas(lang).filter(pl.col("rank") <= VOCAB_TOP).select("lema", "rank", "contagem").iter_rows():
                every = idx[lema.lower()]
                main = lexicon.main_entries(every, lema, upos.get(lema.lower()))
                rows.append(_vocab_row(lema, rank, contagem / total, every, main, english=lang.code == "en"))
        return pl.DataFrame(rows, schema=VOCAB_SCHEMA)

    return memo(f"vocabulario-{lang.code}", build)


def _words(lang: Lang) -> dict[str, conceitos.Word]:
    out: dict[str, conceitos.Word] = {}
    for r in vocabulario(lang).iter_rows(named=True):
        key = r["palavra"].lower()
        if key not in out:
            r = dict(r)
            r.pop("traducoes")
            out[key] = conceitos.Word(lang=lang.code, **{k: set(v) if isinstance(v, list) and k != "glosas" else v for k, v in r.items()})
            # Chinese subtitles' traditional spellings point at the same word.
            if r["tradicional"] and r["tradicional"].lower() not in out:
                out[r["tradicional"].lower()] = out[key]
    return out


def _all_words() -> dict[str, dict[str, conceitos.Word]]:
    return {code: _words(PT if code == "pt" else LANGS[code]) for code in conceitos.ORIGENS}


def alinhamento() -> pl.DataFrame:
    """One row per concept (the 5,000 most frequent English words): its word,
    rank and confirmation in each language."""

    def build() -> pl.DataFrame:
        words = _all_words()
        en = vocabulario(LANGS["en"]).filter(pl.col("rank") <= TOP_WORDS)
        concepts = [conceitos.Concept(r["palavra"], (r["pos"] or ["?"])[0], r["rank"], r["traducoes"]) for r in en.iter_rows(named=True)]
        # Part of speech as the English entry's main one (first in main_entries order).
        main_pos = {r["palavra"]: r["pos"] for r in en.iter_rows(named=True)}
        idx_en = lexicon.index(dicionario(LANGS["en"]))
        upos = upos_by_lemma(LANGS["en"])
        for c in concepts:
            main = lexicon.main_entries(idx_en[c.conceito.lower()], c.conceito, upos.get(c.conceito.lower()))
            c.classe = main[0].pos if main else (main_pos[c.conceito] or ["?"])[0]
        rows = []
        for r in conceitos.align(concepts, words):
            row = {"conceito": r["conceito"], "classe": r["classe"], "rank_en": r["rank_en"]}
            for code in conceitos.ORIGENS:
                w = r.get(code)
                row[f"palavra_{code}"] = w.palavra if w else None
                row[f"rank_{code}"] = w.rank if w else None
                row[f"confirmada_{code}"] = None if code == "en" else (r[f"ok_{code}"] if w else None)
            rows.append(row)
        return pl.DataFrame(rows, infer_schema_length=None)

    return memo("poliglota-alinhamento", build)


def _aligned_words() -> list[dict]:
    """``alinhamento`` with Word objects back in place, for the measures."""
    words = _all_words()
    out = []
    for r in alinhamento().iter_rows(named=True):
        row = {"conceito": r["conceito"]}
        for code in conceitos.ORIGENS:
            p = r[f"palavra_{code}"]
            row[code] = words[code].get(p.lower()) if p else None
        out.append(row)
    return out


def pares() -> pl.DataFrame:
    """Every language pair of every concept, classified (igual, parecida…)."""
    return memo("poliglota-pares", lambda: pl.DataFrame(conceitos.pairs(_aligned_words()), infer_schema_length=None))


def vantagem() -> pl.DataFrame:
    """The advantage matrix: what knowing language A gives you of language B."""
    return memo("poliglota-vantagem", lambda: pl.DataFrame(conceitos.advantage(_aligned_words(), _all_words(), top=TOP_WORDS)))


def falsos_amigos() -> pl.DataFrame:
    """Same spelling, different meaning, between any two of the six languages."""

    def build() -> pl.DataFrame:
        p = pares()
        linked = {(r[0], r[1], r[2], r[3]) for r in p.select("lingua_a", "palavra_a", "lingua_b", "palavra_b").iter_rows()}
        schema = {"lingua_a": pl.String, "palavra_a": pl.String, "rank_a": pl.Int64, "sentido_a": pl.String, "lingua_b": pl.String, "palavra_b": pl.String, "rank_b": pl.Int64, "sentido_b": pl.String}
        return pl.DataFrame(conceitos.false_friend_pairs(_all_words(), linked, top=TOP_WORDS), schema=schema)

    return memo("poliglota-falsos-amigos", build)


def conceitos_lado_a_lado() -> pl.DataFrame:
    """The alignment in wide form for the site: each language's word, its class
    against Portuguese (igual, parecida…) and its IPA."""

    def build() -> pl.DataFrame:
        a = alinhamento()
        p = pares().filter(pl.col("lingua_a") == "pt").select("conceito", "lingua_b", "classe")
        out = a
        for code in conceitos.ALVOS:
            vs_pt = p.filter(pl.col("lingua_b") == code).select("conceito", pl.col("classe").alias(f"vs_pt_{code}"))
            ipa = lemas(LANGS[code]).filter(pl.col("rank") <= VOCAB_TOP).select(pl.col("lema").alias(f"palavra_{code}"), pl.col("ipa").alias(f"ipa_{code}"))
            out = out.join(vs_pt, on="conceito", how="left").join(ipa, on=f"palavra_{code}", how="left")
        targets = [f"palavra_{c}" for c in conceitos.ALVOS if c != "en"]
        return out.with_columns(pl.sum_horizontal([pl.col(t).is_not_null() for t in targets]).alias("n_linguas")).sort("rank_en")

    return memo("poliglota-conceitos", build)
