import io
import sqlite3
import tempfile
import zipfile
from pathlib import Path

from pipeline import anki
from pipeline.langs import LANGS

ES = LANGS["es"]


def row(rank, lema):
    return {
        "rank": rank, "lema": lema, "classe": "verb", "genero": None, "ipa": "/x/", "glosas": ["to be", "to <exist>"],
        "formas": [lema, f"{lema}s"], "frase": f"Yo {lema} aquí.", "forma": lema, "traducao": "Eu aqui.", "frase_id": 7,
    }  # fmt: skip


def test_guid_is_stable_and_language_specific():
    assert anki.guid(ES, "estar") == anki.guid(ES, "estar")
    assert anki.guid(ES, "estar") != anki.guid(LANGS["it"], "estar")


def test_highlight_escapes_and_bolds_whole_word_only():
    assert anki.highlight("Estar o no <estar>", "estar") == "<b>Estar</b> o no &lt;estar&gt;"
    assert anki.highlight("Mientras", "tras") == "Mientras"


def test_deck_contains_band_in_rank_order():
    data = anki.deck_bytes([row(2, "ser"), row(1, "estar"), row(600, "lejos")], ES, (1, 500))
    with tempfile.TemporaryDirectory() as tmp:
        zipfile.ZipFile(io.BytesIO(data)).extractall(tmp)
        db = sqlite3.connect(Path(tmp) / "collection.anki2")
        notes = db.execute("select n.flds, c.due from notes n join cards c on c.nid = n.id order by c.due").fetchall()
        db.close()
    assert [flds.split("\x1f")[0] for flds, _ in notes] == ["estar", "ser"]
    assert [due for _, due in notes] == [1, 2]
    assert "&lt;exist&gt;" in notes[0][0]


def test_archive_is_reproducible():
    decks = {"a.apkg": b"1", "b.apkg": b"2"}
    assert anki.archive(decks) == anki.archive(decks)
    assert zipfile.ZipFile(io.BytesIO(anki.archive(decks))).namelist() == ["a.apkg", "b.apkg"]


def test_poliglota_deck_has_one_note_per_concept_with_portuguese():
    rows = [
        {"conceito": "house", "classe": "noun", "rank_en": 2, "palavra_pt": "casa", "palavra_en": "house", "palavra_es": "casa", "vs_pt_es": "igual",
         "ipa_es": "/ˈkasa/", "palavra_fr": "maison", "vs_pt_fr": "diferente", "palavra_it": "casa", "vs_pt_it": "igual", "palavra_de": "Haus", "vs_pt_de": "parecida"},
        {"conceito": "dog", "classe": "noun", "rank_en": 1, "palavra_pt": None},
    ]  # fmt: skip
    data = anki.poliglota_deck_bytes(rows)
    with tempfile.TemporaryDirectory() as tmp:
        zipfile.ZipFile(io.BytesIO(data)).extractall(tmp)
        db = sqlite3.connect(Path(tmp) / "collection.anki2")
        notes = db.execute("select flds from notes").fetchall()
        db.close()
    assert len(notes) == 1
    flds = notes[0][0].split("\x1f")
    assert flds[0] == "casa" and "igual ao português" in flds[5] and flds[6] == "casa"
    assert anki.poliglota_guid("house", "noun") == anki.poliglota_guid("house", "noun")
