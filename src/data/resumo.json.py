"""Per-language figures for the home page and the methodology page."""

from datetime import datetime, timezone

import polars as pl

from pipeline import anki, frames
from pipeline.io import emit_json
from pipeline.langs import selected


def words_for(cov: pl.DataFrame, share: float) -> int | None:
    hit = cov.filter(pl.col("cobertura") >= share)
    return int(hit["rank"].min()) if hit.height else None


linguas = []
for lang in selected():
    total = frames.total_tokens(lang)
    lm = frames.lemas(lang)
    cov = frames.cobertura(lang)
    pal = frames.palavras(lang)
    fr = frames.frases(lang)
    first = fr.filter(pl.col("ordem") == 1)
    tipos = {r["tipo"]: r["c"] / total for r in lm.group_by("tipo").agg(pl.col("contagem").sum().alias("c")).iter_rows(named=True)}
    status = frames.formas_lemas(lang).filter(pl.col("rank_forma") <= 50_000).group_by("status").agg(pl.col("contagem").sum()).rows()
    linguas.append(
        {
            "codigo": lang.code,
            "nome": lang.nome,
            "tokens": total,
            "fonte": lang.freq_fonte,  # "wordfreq": tokens are proportions scaled to a billion, not a count
            "formas": frames.formas(lang.freq_code).height,
            "palavras_dicionario": int(lm.filter(pl.col("tipo") == "palavra").height),
            "para": {str(int(p * 100)): words_for(cov, p) for p in (0.5, 0.8, 0.9, 0.95)},
            "formas_para": {str(int(p * 100)): (int(cov.filter(pl.col("cobertura_formas") >= p)["rank"].min()) if cov.filter(pl.col("cobertura_formas") >= p).height else None) for p in (0.5, 0.8, 0.9)},
            "cobertura_em": {str(n): float(cov.filter(pl.col("rank") == n)["cobertura"][0]) for n in (100, 500, 1000, 2000, 3000, 5000, 10000) if n <= cov.height},
            "parcela": {"palavras": tipos.get("palavra", 0), "nomes": tipos.get("nome próprio", 0), "fora": tipos.get("fora do dicionário", 0)},
            "status_formas": {s: c / total for s, c in status},
            "com_frase": first.height,
            "frase_traduzida_pt": first.filter(pl.col("lingua_traducao") == "pt").height,
            "frase_ao_alcance": first.filter(pl.col("ao_alcance")).height,
            "com_ipa": pal.filter(pl.col("ipa").is_not_null()).height,
            "classes": pal.group_by("classe").agg(pl.len().alias("n")).sort("n", descending=True).head(8).to_dicts(),
            "baralhos": [{"arquivo": anki.file_name(lang, b), "de": b[0], "ate": b[1], "nome": anki.deck_name(lang, b)} for b in anki.BANDS],
        }
    )

emit_json({"gerado_em": datetime.now(timezone.utc).isoformat(timespec="seconds"), "palavras_por_lingua": frames.TOP_WORDS, "linguas": linguas})
