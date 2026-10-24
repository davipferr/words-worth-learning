import polars as pl

from pipeline.examples import choose
from pipeline.langs import LANGS


def test_prefers_translated_sentence_within_reach():
    lemas = pl.DataFrame({"lema": ["ser", "la", "casa", "grande", "tom"], "rank": [1, 2, 50, 4000, None], "tipo": ["palavra", "palavra", "palavra", "palavra", "nome próprio"]})
    formas_lemas = pl.DataFrame({"forma": ["es", "casa", "grande", "tom", "la"], "lema": ["ser", "casa", "grande", "tom", "la"]})
    sentences = pl.DataFrame(
        {
            "id": [1, 2, 3],
            "texto": ["La casa es grande.", "Tom es casa casa.", "Es la casa."],
            "trad_pt": ["A casa é grande.", None, "É a casa."],
            "trad_en": [None, "Tom is house.", None],
        }
    )
    out = choose(sentences, formas_lemas, lemas, LANGS["es"], top=5000)
    casa = out.filter(pl.col("lema") == "casa").sort("ordem")
    # Sentence 3 has a Portuguese translation and nothing rarer than "casa";
    # sentence 1 has "grande" (rank 4000), out of reach for a rank-50 word.
    assert casa["frase_id"].to_list()[0] == 3
    assert casa.filter(pl.col("frase_id") == 1)["dificuldade"].item() == 4000
    # The English-only sentence comes last.
    assert casa["frase_id"].to_list()[-1] == 2
