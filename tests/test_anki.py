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
