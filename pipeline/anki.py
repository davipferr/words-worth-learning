"""Anki decks (.apkg) built at build time with genanki.

One deck per language and frequency band ("Espanhol 0001–0500"…), nested
under "Palavras que valem a pena", one note per word. Notes have stable IDs
(GUIDs from language + word), so importing a rebuilt deck updates the cards
you already have — and keeps their review history — instead of duplicating
them. A word that moves to another band keeps its cards in the deck where
they already are.

The front shows the word with Anki's built-in text-to-speech (``{{tts}}``,
which uses the voices of your phone or computer, so no audio is bundled); the
back has the pronunciation, Wiktionary's definitions as written, the most
common forms and an example sentence with its translation.
"""

from __future__ import annotations

import hashlib
import html
import io
import re
import tempfile
import zipfile
from pathlib import Path

import genanki
import polars as pl

from .langs import GENEROS, Lang, classe

BANDS = [(1, 500), (501, 1000), (1001, 2000), (2001, 3000), (3001, 5000)]
ROOT_DECK = "Palavras que valem a pena"
MODEL_ID = 1726448123  # fixed forever: Anki matches note types by ID

FIELDS = ["Palavra", "Classe", "IPA", "Definicao", "Formas", "Frase", "Traducao", "Posicao", "Fonte"]

FRONT = """<div class="palavra">{{Palavra}}</div>
<div class="classe">{{Classe}}</div>
{{tts %(tts)s:Palavra}}"""

BACK = """{{FrontSide}}
<hr id="answer">
{{#IPA}}<div class="ipa">{{IPA}}</div>{{/IPA}}
<div class="definicao">{{Definicao}}</div>
{{#Frase}}<div class="frase">{{Frase}} {{tts %(tts)s:Frase}}</div>
<div class="traducao">{{Traducao}}</div>{{/Frase}}
{{#Formas}}<div class="formas">Formas mais comuns: {{Formas}}</div>{{/Formas}}
<div class="posicao">{{Posicao}}{{#Fonte}} · {{Fonte}}{{/Fonte}}</div>"""

CSS = """.card { font-family: "IBM Plex Sans", -apple-system, "Segoe UI", Roboto, sans-serif; font-size: 18px;
  text-align: center; color: #1b1b1a; background: #fbfbf9; line-height: 1.45; padding: 0 12px; }
.nightMode.card, .night_mode .card { color: #ecebe6; background: #161615; }
.palavra { font-size: 40px; font-weight: 600; margin-top: 18px; }
.classe { font-size: 14px; color: #7a7974; margin-top: 2px; }
.ipa { font-size: 18px; color: #2a78d6; margin: 6px 0; }
.nightMode .ipa { color: #6da7ec; }
.definicao { text-align: left; max-width: 34em; margin: 10px auto; }
.definicao ol { margin: 0; padding-left: 1.3em; }
.frase { font-size: 20px; margin-top: 16px; }
.frase b { color: #2a78d6; }
.nightMode .frase b { color: #6da7ec; }
.traducao { font-size: 16px; color: #7a7974; font-style: italic; }
.formas, .posicao { font-size: 13px; color: #7a7974; margin-top: 12px; }
.posicao a { color: inherit; }"""


def model(lang: Lang) -> genanki.Model:
    """One note type per language, so ``{{tts}}`` uses that language's voice."""
    return genanki.Model(
        MODEL_ID + _int(lang.code) % 1_000_000,
        f"Palavras que valem a pena ({lang.nome})",
        fields=[{"name": f} for f in FIELDS],
        templates=[{"name": "Reconhecer", "qfmt": FRONT % {"tts": lang.tts}, "afmt": BACK % {"tts": lang.tts}}],
        css=CSS,
        sort_field_index=FIELDS.index("Posicao"),
    )


def _int(text: str) -> int:
    return int(hashlib.sha256(text.encode()).hexdigest()[:12], 16)


def guid(lang: Lang, lema: str) -> str:
    """Stable note ID: same language and word -> same note, build after build."""
    return genanki.guid_for("wwl", lang.code, lema)


def deck_name(lang: Lang, band: tuple[int, int]) -> str:
    return f"{ROOT_DECK}::{lang.nome}::{band[0]:04d}–{band[1]:04d}"


def file_name(lang: Lang, band: tuple[int, int]) -> str:
    return f"{lang.code}-{band[0]:04d}-{band[1]:04d}.apkg"


def highlight(sentence: str, form: str | None) -> str:
    """HTML-escaped sentence with the word's occurrence in bold."""
    text = html.escape(sentence)
    if not form:
        return text
    pattern = re.compile(rf"(?<![^\W\d_]){re.escape(html.escape(form))}(?![^\W\d_])", re.IGNORECASE)
    return pattern.sub(lambda m: f"<b>{m.group(0)}</b>", text, count=1)


def definition(glosas: list[str] | None) -> str:
    items = [html.escape(g) for g in glosas or []]
    if len(items) <= 1:
        return items[0] if items else ""
    return "<ol>" + "".join(f"<li>{g}</li>" for g in items) + "</ol>"


def fields(r: dict, lang: Lang) -> list[str]:
    cls = classe(r["classe"])
    if r.get("genero"):
        cls += f", {GENEROS.get(r['genero'], r['genero'])}"
    frase_id = r.get("frase_id")
    return [
        html.escape(r["lema"]),
        cls,
        html.escape(r["ipa"] or ""),
        definition(r["glosas"]),
        html.escape(", ".join(f for f in r["formas"] or [] if f != r["lema"].lower())[:120]),
        highlight(r["frase"], r.get("forma")) if r.get("frase") else "",
        html.escape(r.get("traducao") or ""),
        f"nº {r['rank']} em frequência",
        f'<a href="https://tatoeba.org/pt-br/sentences/show/{frase_id}">Tatoeba #{frase_id}</a>' if frase_id else "",
    ]


def note(r: dict, lang: Lang, mdl: genanki.Model) -> genanki.Note:
    tags = [f"wwl::{lang.code}", f"classe::{classe(r['classe']).replace(' ', '_')}"]
    # Sort by rank: zero-padded so Anki's text sort matches the number.
    f = fields(r, lang)
    # due = rank: Anki introduces new cards in ascending "due" order.
    return genanki.Note(model=mdl, fields=f, guid=guid(lang, r["lema"]), tags=tags, sort_field=f"{r['rank']:05d}", due=r["rank"])


def deck_bytes(rows: list[dict], lang: Lang, band: tuple[int, int]) -> bytes:
    """One .apkg with the words of ``band``, in frequency order (Anki shows
    new cards in the order they were added)."""
    mdl = model(lang)
    name = deck_name(lang, band)
    deck = genanki.Deck(_int(name) % (1 << 31), name, description=f"As palavras {band[0]} a {band[1]} mais frequentes do {lang.nome.lower()} em legendas de filmes e séries.")
    for r in sorted(rows, key=lambda r: r["rank"]):
        if band[0] <= r["rank"] <= band[1]:
            deck.add_note(note(r, lang, mdl))
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "deck.apkg"
        # A fixed timestamp keeps rebuilt decks byte-identical when nothing changed.
        genanki.Package(deck).write_to_file(path, timestamp=1_700_000_000)
        return path.read_bytes()


def cards(palavras: pl.DataFrame, frases: pl.DataFrame) -> pl.DataFrame:
    """Words joined with their first example sentence: one row per future note."""
    first = frases.filter(pl.col("ordem") == 1).select("lema", "frase_id", pl.col("texto").alias("frase"), "forma", "traducao")
    return palavras.join(first, on="lema", how="left").sort("rank")


def archive(decks: dict[str, bytes]) -> bytes:
    """Zip of every deck, for Framework's archive loader (``decks.zip``)."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_STORED) as zf:  # .apkg files are already compressed
        for name, data in decks.items():
            zf.writestr(zipfile.ZipInfo(name, date_time=(2024, 1, 1, 0, 0, 0)), data)
    return buf.getvalue()
