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
    return package(deck)


def package(deck: genanki.Deck) -> bytes:
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


# ----------------------------------------------------------------- poliglota
#
# One note per concept (see ``conceitos``): the Portuguese word on the front,
# the word in each of the five languages on the back, each marked by how much
# it looks like the Portuguese one. Studying them together shows the patterns
# ("-ción", "-zione", "-tion" all are "-ção").

POLIGLOTA_MODEL_ID = 1726448999
POLIGLOTA_DECK = f"{ROOT_DECK}::Poliglota"
POLIGLOTA_FILE = "poliglota.apkg"
LINGUAS_DECK = [("en", "Inglês", "en_US"), ("es", "Espanhol", "es_ES"), ("fr", "Francês", "fr_FR"), ("it", "Italiano", "it_IT"), ("de", "Alemão", "de_DE")]
MARCAS = {"igual": "igual ao português", "parecida": "parecida", "mesma origem": "mesma origem", "diferente": ""}

def _campo(lang_nome: str) -> str:
    """Anki field name for a language: ASCII, "Francês" -> "Frances"."""
    return lang_nome.replace("ê", "e").replace("ã", "a")


POLIGLOTA_FRONT = """<div class="palavra">{{Portugues}}</div>
<div class="classe">{{Classe}} · em inglês: {{Conceito}}</div>"""

POLIGLOTA_BACK = (
    """{{FrontSide}}
<hr id="answer">
<table class="linguas">"""
    + "".join(f"""
<tr><th>{nome}</th><td>{{{{{_campo(nome)}}}}}</td><td class="tts">{{{{#{_campo(nome)}Texto}}}}{{{{tts {voz}:{_campo(nome)}Texto}}}}{{{{/{_campo(nome)}Texto}}}}</td></tr>""" for _, nome, voz in LINGUAS_DECK)
    + """
</table>
<div class="posicao">{{Posicao}}</div>"""
)

POLIGLOTA_CSS = (
    CSS
    + """
.linguas { margin: 12px auto; border-collapse: collapse; font-size: 20px; }
.linguas th { text-align: right; font-weight: 400; font-size: 13px; color: #7a7974; padding: 4px 12px 4px 0; }
.linguas td { text-align: left; padding: 4px 0; }
.linguas td.tts { padding-left: 8px; }
.ipa-mini { font-size: 13px; color: #7a7974; margin-left: 6px; }
.marca { font-size: 11px; border-radius: 999px; padding: 1px 7px; margin-left: 6px; vertical-align: middle; }
.marca.igual { background: #1baf7a; color: #fff; }
.marca.parecida { background: #2a78d6; color: #fff; }
.marca.origem { border: 1px solid #7a7974; color: #7a7974; }"""
)


def poliglota_model() -> genanki.Model:
    fields = ["Portugues", "Conceito", "Classe"]
    for _, nome, _ in LINGUAS_DECK:
        fields += [_campo(nome), f"{_campo(nome)}Texto"]
    fields.append("Posicao")
    return genanki.Model(
        POLIGLOTA_MODEL_ID,
        "Palavras que valem a pena (Poliglota)",
        fields=[{"name": f} for f in fields],
        templates=[{"name": "Cinco línguas", "qfmt": POLIGLOTA_FRONT, "afmt": POLIGLOTA_BACK}],
        css=POLIGLOTA_CSS,
        sort_field_index=fields.index("Posicao"),
    )


def poliglota_fields(r: dict) -> list[str]:
    out = [html.escape(r["palavra_pt"]), html.escape(r["conceito"]), classe(r["classe"])]
    for code, _, _ in LINGUAS_DECK:
        word = r.get(f"palavra_{code}")
        if not word:
            out += ["—", ""]
            continue
        cls = r.get(f"vs_pt_{code}")
        css = {"igual": "igual", "parecida": "parecida", "mesma origem": "origem"}.get(cls)
        cell = html.escape(word)
        if r.get(f"ipa_{code}"):
            cell += f'<span class="ipa-mini">{html.escape(r[f"ipa_{code}"])}</span>'
        if css:
            cell += f'<span class="marca {css}">{MARCAS[cls]}</span>'
        out += [cell, html.escape(word)]
    out.append(f"conceito nº {r['rank_en']}")
    return out


def poliglota_guid(conceito: str, classe_: str) -> str:
    return genanki.guid_for("wwl-poliglota", conceito, classe_)


def poliglota_deck_bytes(rows: list[dict]) -> bytes:
    """Concepts that have a Portuguese word, in English frequency order."""
    mdl = poliglota_model()
    deck = genanki.Deck(
        _int(POLIGLOTA_DECK) % (1 << 31),
        POLIGLOTA_DECK,
        description="O mesmo conceito em inglês, espanhol, francês, italiano e alemão, a partir do português.",
    )
    for due, r in enumerate(sorted((r for r in rows if r.get("palavra_pt")), key=lambda r: r["rank_en"]), 1):
        deck.add_note(
            genanki.Note(
                model=mdl,
                fields=poliglota_fields(r),
                guid=poliglota_guid(r["conceito"], r["classe"]),
                tags=["wwl::poliglota", f"classe::{classe(r['classe']).replace(' ', '_')}"],
                sort_field=f"{r['rank_en']:05d}",
                due=due,
            )
        )
    return package(deck)
