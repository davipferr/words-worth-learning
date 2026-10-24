import polars as pl

from pipeline.langs import LANGS
from pipeline.lexicon import Entry, index, lemmatize, main_entries, resolve
from pipeline.wiktionary import SCHEMA


def entry(palavra, pos, glosas=(), forma_de=(), genero=None):
    return {"palavra": palavra, "pos": pos, "glosas": list(glosas), "forma_de": list(forma_de), "genero": genero, "ipa": None, "etimo": None}


DIC = pl.DataFrame(
    [
        entry("estar", "verb", ["to be"]),
        entry("estoy", "verb", forma_de=["estar"]),
        entry("ser", "verb", ["to be"]),
        entry("ir", "verb", ["to go"]),
        entry("fue", "verb", forma_de=["ser", "ir"]),
        entry("como", "adv", ["as", "like", "how"]),
        entry("como", "verb", forma_de=["comer"]),
        entry("comer", "verb", ["to eat"]),
        entry("flor", "noun", ["flower"]),
        entry("flores", "noun", ["menstruation"]),
        entry("flores", "noun", forma_de=["flor"]),
        entry("de", "noun", ["The name of the Latin-script letter D."]),
        entry("de", "prep", ["of", "from"]),
        entry("María", "name", ["a female given name"]),
        entry("do", "verb", ["to do"]),
    ],
    schema=SCHEMA,
)
IDX = index(DIC)
ES, EN = LANGS["es"], LANGS["en"]


def test_inflection_goes_to_lemma_and_splits_when_ambiguous():
    assert resolve("estoy", IDX, ES) == ("flexão", [("estar", 1.0)])
    assert resolve("fue", IDX, ES) == ("flexão", [("ser", 0.5), ("ir", 0.5)])


def test_substantial_lemma_keeps_its_count_but_one_sense_entries_do_not():
    assert resolve("como", IDX, ES) == ("lema", [("como", 1.0)])
    assert resolve("flores", IDX, ES) == ("flexão", [("flor", 1.0)])


def test_treebank_decides_when_it_saw_the_form():
    ud = {"como": [("como", "SCONJ", 8), ("comer", "VERB", 2)]}
    status, lemmas = resolve("como", IDX, ES, ud)
    assert status == "flexão" and lemmas == [("como", 0.8), ("comer", 0.2)]
    # Treebank says proper noun -> never a word to learn.
    assert resolve("maría", IDX, ES, {"maría": [("María", "PROPN", 5)]})[0] == "nome próprio"


def test_contraction_halves_and_unknown_tokens():
    assert resolve("don", IDX, EN) == ("contração", [("do", 1.0)])
    assert resolve("xyzzy", IDX, ES) == ("fora do dicionário", [("xyzzy", 1.0)])
    assert resolve("maría", IDX, ES)[0] == "nome próprio"


def test_letter_entries_go_last():
    entries = main_entries(IDX["de"], "de")
    assert [e.pos for e in entries] == ["prep", "noun"]
    assert isinstance(entries[0], Entry)


def test_lemmatize_weights_sum_to_one_per_form():
    formas = pl.DataFrame({"forma": ["fue", "estoy", "rara"], "contagem": [10, 5, 1]})
    fl = lemmatize(formas, IDX, ES, top=2)
    assert fl.group_by("forma").agg(pl.col("peso").sum()).sort("forma")["peso"].to_list() == [1.0, 1.0, 1.0]
    # Beyond ``top`` every form counts as itself.
    assert fl.filter(pl.col("forma") == "rara")["status"].item() == "fora do dicionário"


def test_treebank_lemma_follows_form_of_when_parts_of_speech_disagree():
    dic = pl.DataFrame(
        [
            entry("mío", "pron", ["mine"]),
            entry("mi", "det", forma_de=["mío"]),
            entry("mi", "noun", ["mi (musical note)"]),
        ],
        schema=SCHEMA,
    )
    idx = index(dic)
    assert resolve("mi", idx, ES, {"mi": [("mi", "DET", 9)]}) == ("flexão", [("mío", 1.0)])
