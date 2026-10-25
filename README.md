# Palavras que valem a pena (words worth learning)

A static site that answers **which words should I learn first?** for English, Spanish, French, Italian, German, Japanese and Chinese, turns the answer into **Anki decks**, and measures **how much one language gives you of another** (Portuguese included as the starting point). It counts every word in OpenSubtitles (movie and TV subtitles), groups the inflected forms of each dictionary word ("estoy", "estaba", "estuvo" → *estar*) and ranks the 5,000 most useful words per language. Built with a Python pipeline (**Polars**, **genanki**) and **Observable Framework** (Observable Plot for charts, DuckDB-WASM for in-browser SQL). The site is in Portuguese.

Every download happens **at build time** in Framework data loaders. The browser only gets pre-built Parquet/JSON files and the `.apkg` decks.

Two sections, as in `forecasts-vs-reality` (`pages` groups in `observablehq.config.js`, one folder per section under `src/`):

| Section / page | What it shows |
|---|---|
| Início | One card per section |
| **Vocabulário** › Visão geral | Coverage curves for the five languages; words needed for 80 % and 90 % per language |
| Cobertura | Words needed for 50–95 % coverage, diminishing returns per frequency band, lemmas vs. forms, what never counts (names, unknown tokens) |
| Palavras | The ranked list with filters (word class, frequency band, has an example), a word card (IPA, Wiktionary definitions, forms, etymology, three example sentences) and a text export the Anki importer reads |
| Baralhos Anki | 35 ready-made decks (7 languages × 5 bands: 1–500, 501–1,000, 1,001–2,000, 2,001–3,000, 3,001–5,000), card preview, how to import |
| **Poliglota** › Visão geral | The advantage matrix: share of what is said in each language that is recognisable from another (rows: Portuguese + the five languages) |
| Vantagem de partida | The matrix by measure (recognisable, same origin, aligned), "which language next?" for the languages you know, and every word pair of a chosen pair of languages |
| Conceitos lado a lado | 5,000 concepts in six languages, coloured by similarity to Portuguese; a multilingual Anki deck and a filterable text export |
| Falsos amigos | Same spelling, different meaning, between any two of the six languages (*pain*: en "pain", fr "bread") |
| Consulta SQL | Free-form SQL over the Parquet files with DuckDB-WASM |
| Sobre os dados | Sources, the lemmatisation rules, sentence choice, limitations |

## Findings (October 2026 data)

- **A thousand words go a long way.** In the European languages, the 1,000 most frequent words cover 81 % (Italian) to 86 % (English) of everything said in subtitles; in Japanese 75 %, in Chinese 70 %.
- **The last stretch is expensive.** Reaching 90 % takes 1,877 words in English, 2,047 in French, 2,599 in Spanish, 3,830 in German, 4,227 in Italian and 6,559 in Japanese; Chinese doesn't get there within 10,000 words (81 % at 5,000), since its subtitle words are segmented into many compounds. Japanese frequencies come from mixed sources (wordfreq), so its figures are less comparable.
- **The first hundred words do half the work.** They cover 58 % (Italian) to 67 % (French) of all tokens.
- **Learning lemmas beats learning forms.** In Spanish, 577 dictionary words reach 80 % coverage; learning forms one by one would take 1,810. The gap is smallest in English (431 vs. 659), which barely inflects.

- **Portuguese gives you half of Spanish.** 56 % of what is said in Spanish subtitles is words identical or similar to their Portuguese equivalent; 40 % of Italian, 32 % of French, but only 7–8 % of English and German, and almost nothing of Japanese (katakana loans such as パン, from *pão*) or Chinese.
- **Spanish and Italian are the closest foreign pair** (47 % of Italian recognisable from Spanish, 48 % the other way); English and German help each other about 20 %. Japanese and Chinese share 399 concepts written with the same characters, but only about 3 % of tokens, because Japanese grammar is written in kana.

## Anki decks

- One note per word. The front shows the word and its class, read aloud by Anki's built-in `{{tts}}` (no audio files are bundled). The back has the IPA, Wiktionary's definitions **as written (in English, not translated)**, the most common forms and an example sentence from Tatoeba with its translation (Portuguese when Tatoeba has one, otherwise English).
- **Stable GUIDs** (from language + word): re-importing a rebuilt deck updates existing notes and keeps their review history. New cards are due in frequency order.
- **Poliglota deck** (`poliglota.apkg`): one note per concept that has a Portuguese word (4,045; 2,281 have a word in all eight languages), the Portuguese word on the front and the five languages on the back, each with IPA, a similarity badge and `{{tts}}`.
- The Palavras page also exports any filtered selection as an Anki text file (`#separator:tab`, `#html:true`, `#guid column:4`, no column labels; Anki ≥ 2.1.55), for custom decks such as "only verbs".

## Quick start

Requirements: [uv](https://docs.astral.sh/uv/) and Node.js ≥ 18. No API key needed.

```bash
uv sync          # Python env (polars, duckdb, httpx, orjson, genanki, pytest)
npm install      # Observable Framework
npm run dev      # http://127.0.0.1:3000
npm run build    # static site in dist/
```

The first build downloads about **1 GB** (the English Wiktionary dump alone is 534 MB) and takes around **10 minutes**. Raw files are cached in `data_cache/raw/` (frequency lists forever, Wiktionary 90 days, Tatoeba 30 days, treebanks 180 days), and parsed tables in `data_cache/frames/`, so later builds take about a minute.

Knobs (environment variables):

| Variable | Default | Effect |
|---|---|---|
| `WWL_LANGS` | `en,es,fr,it,de` | Languages to build. `src/anki.md` lists all 25 deck files by name (Framework needs literal file names), so a subset build needs that list trimmed too |
| `WWL_CACHE_DIR` | `data_cache` | Where raw downloads and memoised frames live |

## Data sources

| Source | Used for | License |
|---|---|---|
| [FrequencyWords](https://github.com/hermitdave/FrequencyWords), OpenSubtitles 2018 full lists | Count of every word form per language | CC BY-SA 4.0 |
| [kaikki.org](https://kaikki.org) extraction of the English Wiktionary | Form → lemma links, part of speech, definitions, IPA, gender, etymology | CC BY-SA 4.0 |
| [Universal Dependencies](https://universaldependencies.org) (EWT, AnCora, French GSD, ISDT, German GSD, Japanese GSD, Chinese GSDSimp) | P(lemma \| form) for ambiguous forms | CC BY-SA 4.0 / CC BY 4.0 / CC BY-NC-SA 3.0 (ISDT) |
| [wordfreq](https://github.com/rspeer/wordfreq) | Japanese frequencies (MeCab-segmented; subtitles + Wikipedia + news + social media). FrequencyWords' Japanese list lost all hiragana | CC BY-SA 4.0 |
| [CC-CEDICT](https://cc-cedict.org) | Chinese definitions and pinyin, one line per reading (picked by the Chinese treebank's transliteration) | CC BY-SA 4.0 |
| [Tatoeba](https://tatoeba.org) per-language exports | Example sentences and their Portuguese/English translations | CC BY 2.0 FR |

## How it works

### Vocabulário

Forms are mapped to lemmas in this order (`pipeline/lexicon.py`):

1. Contraction halves left by the tokenizer go to their word (`don` → *do*, `c'` → *ce*).
2. If the treebank saw the form at least 3 times, its count is split the way annotators lemmatised it there (`anda` → *andar*; `como` → mostly the conjunction).
3. Otherwise Wiktionary: a form with its own definitions counts for itself unless it is also an inflection and has a single sense (`flores` → *flor*); a pure inflection splits its count evenly between its lemmas (`fue` → *ser*/*ir*).
4. Proper nouns and tokens missing from Wiktionary stay in the total but are never ranked or counted as covered.

Example sentences (`pipeline/examples.py`) follow the *i*+1 idea: prefer a Portuguese translation, then a sentence whose rarest other word is no rarer than the word itself (or within the top 300), then a length near eight words.

### Japanese and Chinese

- Both lists are already segmented (Chinese subtitles; wordfreq for Japanese). Tatoeba sentences are segmented by longest match against the 50,000 most frequent forms. Latin-script tokens (English lines in bilingual subtitles) are dropped from the totals.
- Japanese verb and adjective pieces (書き, 書い from 書いた) map to their lemma through Wiktionary's conjugation tables; the reading is kana + romaji.
- Chinese doesn't inflect, so the treebank's lemmas aren't used (it reduces 我们 to 我); traditional spellings count for the simplified word.

### Poliglota

- **Concepts** are the 5,000 most frequent English words. Their equivalents come from that English entry's Wiktionary translation table (same part of speech only). A candidate must be among its language's 10,000 most frequent words (Portuguese: 30,000 most frequent subtitle forms); the winner is the one whose *own* first definition names the concept, then any definition, then frequency (`pipeline/conceitos.py`).
- **Similarity** (`pipeline/cognates.py`). Japanese and Chinese compare with Latin-script languages only through Japanese katakana loanwords (by romaji: パン ≈ pão); with each other, by characters (Japanese 電話 = Chinese 電話/电话). Classes: *igual* (same spelling without accents), *parecida* (one edit, or ≥ half the letters in place), *mesma origem* (a shared Wiktionary ancestor other than Proto-Indo-European, or a listed cognate), *diferente*.
- **Advantage** of A over B: subtitle share of B's top-5,000 words whose equivalent in A is igual or parecida. Unaligned words count as not recognised, so it is a lower bound.
- **False friends**: same spelling in two top-5,000 lists, no shared concept, and no shared meaning between their English definitions.

```
pipeline/            Python package: one module per concern
  http.py            streaming cached downloads with retries
  langs.py           languages, source names, tokenizer and contraction rules
  freq.py            OpenSubtitles frequency lists
  wiktionary.py      kaikki.org JSONL -> compact entries
  ud.py              CoNLL-U treebanks -> (form, lemma, upos) counts
  tatoeba.py         sentences + translation links
  text.py            tokenizer matching the frequency lists, accent folding
  lexicon.py         forms -> lemmas
  examples.py        readable example sentences
  conceitos.py       Poliglota: concept alignment, advantage matrix, false friends
  cognates.py        similarity classes, shared origin, false-friend rules
  cedict.py          CC-CEDICT parse, pinyin tone marks, reading choice
  anki.py            .apkg decks with genanki (per-language bands + the Poliglota deck)
  frames.py          frames memoised as Parquet (heavy parses keyed on their own module only)
  manifest.py        build manifest + comparison with the live site (CI job summary)
  schema.py / io.py  fail-fast column checks; stdout writers (int64 -> int32)
src/data/*.py        Framework data loaders (thin; run via `uv run`)
src/components/      formatting (pt-BR), palette, charts, Anki text export
src/vocabulario/     section 1 pages
src/poliglota/       section 2 pages
src/*.md             home, SQL console, about
tests/               offline tests
```

## Limitations

- Subtitles are scripted speech, with more dialogue, swearing and foreign snippets than real conversation.
- Senses are not separated: "banco" (bench) and "banco" (bank) count together.
- The frequency lists are lower-cased, so German "Essen" (food) and "essen" (to eat) merge.
- Definitions are Wiktionary's, in English; no translation step.
- Poliglota aligns grammatical words poorly (English "you", "will" have no single equivalent); content words align well.
