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

from . import examples, freq, lexicon, tatoeba, ud, wiktionary
from .http import CACHE_DIR, log
from .langs import PT, Lang
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
        keep = set(formas(lang.code)["forma"].to_list()) | set(lang.contracoes.values())
        log(f"parsing Wiktionary ({lang.kaikki}) for {len(keep):,} subtitle forms")
        return require_columns(wiktionary.entries_en(lang.kaikki, keep), ["palavra", "pos", "glosas", "forma_de"], f"kaikki {lang.kaikki}", min_rows=5_000)

    return memo(f"dic-{lang.code}", build, deps=("wiktionary", "freq", "text", "langs"), max_age=RAW_AGE)


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
    return memo(f"formas-lemas-{lang.code}", lambda: lexicon.lemmatize(formas(lang.code), lexicon.index(dicionario(lang)), lang, treebank(lang)))


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
        learnable = [any(e.is_lemma for e in idx.get(w.lower(), [])) for w in agg["lema"].to_list()]
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
        info = []
        for lema, rank in words.select("lema", "rank").iter_rows():
            if rank > TOP_LEMMAS:
                break
            every = idx[lema.lower()]
            main = lexicon.main_entries(every, lema, upos.get(lema.lower()))
            glosas: list[str] = []
            for e in main:
                for g in e.glosas:
                    if len(glosas) < 4 and g not in glosas:
                        glosas.append(g)
            info.append(
                {
                    "lema": lema,
                    "classe": main[0].pos,
                    "classes": list(dict.fromkeys(e.pos for e in main)),
                    "genero": main[0].genero if main[0].pos == "noun" else None,
                    "ipa": next((e.ipa for e in main if e.ipa), None) or next((e.ipa for e in every if e.ipa), None),
                    "etimo": next((e.etimo for e in main if e.etimo), None),
                    "glosas": glosas,
                }
            )
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
        f = formas(lang.code).head(TOP_LEMMAS).select(
            pl.int_range(1, pl.len() + 1).alias("rank"), (pl.col("contagem").cum_sum() / total).alias("cobertura_formas")
        )
        return w.join(f, on="rank", how="left").sort("rank")

    return memo(f"cobertura-{lang.code}", build)


def total_tokens(lang: Lang) -> int:
    return int(formas(lang.code)["contagem"].sum())
