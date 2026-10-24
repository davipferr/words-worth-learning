"""Data manifest: what each build was made from, and how it compares to the last one.

``build()`` records the code version, when each source file was downloaded and
row counts / coverage of every language. The site publishes it at a stable URL
(``/manifest.json``), so CI can fetch the live copy before deploying and report
what changed:

    python -m pipeline.manifest publish                     # dist/_file/... -> dist/manifest.json
    python -m pipeline.manifest compare previous.json dist/manifest.json

``compare`` warns on any metric that dropped by more than ``--threshold``
(default 10 %) and on output columns that disappeared — the usual signature of
a source that changed shape or a join that broke. It never fails the build
unless ``--strict`` is given.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

import polars as pl

from . import freq, frames, tatoeba, ud, wiktionary
from .http import ROOT, cached_path
from .langs import PT, selected


def _iso(ts: float) -> str:
    return datetime.fromtimestamp(ts, timezone.utc).isoformat(timespec="seconds")


def _source(nome: str, url: str) -> dict:
    path = cached_path(url)
    return {"nome": nome, "url": url, "baixado_em": _iso(path.stat().st_mtime) if path else None}


def sources() -> list[dict]:
    out = []
    for lang in selected():
        out += [
            _source(f"OpenSubtitles (FrequencyWords) — {lang.nome}", freq.url(lang.code)),
            _source(f"Wiktionary (kaikki.org) — {lang.nome}", wiktionary.url_en(lang.kaikki)),
            _source(f"Tatoeba — frases em {lang.nome.lower()}", tatoeba.sentences_url(lang.tatoeba)),
            *[_source(f"Universal Dependencies — {lang.ud.split('/')[0]}", u) for u in ud.urls(lang.ud)[:1]],
        ]
    out.append(_source("Tatoeba — frases em português", tatoeba.sentences_url(PT.tatoeba)))
    out.append(_source("Wiktionary (kaikki.org) — Português", wiktionary.url_en(PT.kaikki)))
    return out


def build() -> dict:
    tabelas = {}
    for lang in selected():
        pal = frames.palavras(lang)
        fr = frames.frases(lang)
        cov = frames.cobertura(lang)
        tabelas[lang.code] = {
            "linhas": pal.height,
            "colunas": pal.columns,
            "tokens": frames.total_tokens(lang),
            "com_frase": fr.filter(pl.col("ordem") == 1).height,
            "com_ipa": pal.filter(pl.col("ipa").is_not_null()).height,
            "cobertura_1000_pct": round(float(cov.filter(pl.col("rank") == 1000)["cobertura"][0]) * 100, 2),
            "cobertura_5000_pct": round(float(cov.filter(pl.col("rank") == 5000)["cobertura"][0]) * 100, 2),
        }
    conc = frames.conceitos_lado_a_lado()
    vant = frames.vantagem()
    tabelas["poliglota"] = {
        "linhas": conc.height,
        "colunas": conc.columns,
        "conceitos_completos": conc.filter(pl.col("palavra_pt").is_not_null(), pl.col("n_linguas") == 4).height,
        "pares": frames.pares().height,
        "falsos_amigos": frames.falsos_amigos().height,
        **{f"pt_{r['alvo']}_reconhecivel_pct": round(r["reconhecivel"] * 100, 2) for r in vant.filter(pl.col("origem") == "pt").iter_rows(named=True)},
    }
    return {
        "gerado_em": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "commit": os.environ.get("GITHUB_SHA"),
        "codigo_pipeline": frames.CODE_VERSION,
        "fontes": sources(),
        "tabelas": tabelas,
    }


# ------------------------------------------------------------------- compare


def _numbers(d: dict, prefix: str = "") -> dict[str, float]:
    """Flatten numeric leaves: {"es": {"linhas": 3}} -> {"es.linhas": 3}."""
    out: dict[str, float] = {}
    for k, v in d.items():
        key = f"{prefix}{k}"
        if isinstance(v, dict):
            out |= _numbers(v, f"{key}.")
        elif isinstance(v, (int, float)) and not isinstance(v, bool):
            out[key] = v
    return out


def _fmt(v: float | None) -> str:
    if v is None:
        return "—"
    return f"{v:,.0f}" if abs(v) >= 100 or float(v).is_integer() else f"{v:,.4g}"


def compare(old: dict, new: dict, threshold: float = 0.10) -> tuple[str, list[str]]:
    """Markdown report of changed metrics, and the list of warnings."""
    warnings: list[str] = []
    rows: list[str] = []
    a, b = _numbers(old.get("tabelas", {})), _numbers(new.get("tabelas", {}))
    unchanged = 0
    for key in sorted(a.keys() | b.keys()):
        va, vb = a.get(key), b.get(key)
        if va == vb:
            unchanged += 1
            continue
        change = (vb - va) / abs(va) if va not in (None, 0) and vb is not None else None
        flag = ""
        if vb is None:
            flag = "⚠"
            warnings.append(f"{key} disappeared (was {_fmt(va)})")
        elif change is not None and change < -threshold:
            flag = "⚠"
            warnings.append(f"{key} dropped {-change:.0%}: {_fmt(va)} → {_fmt(vb)}")
        rows.append(f"| {f'{flag} ' if flag else ''}`{key}` | {_fmt(va)} | {_fmt(vb)} | {'—' if change is None else f'{change:+.1%}'} |")

    for name, table in new.get("tabelas", {}).items():
        before = set(old.get("tabelas", {}).get(name, {}).get("colunas", []))
        after = set(table.get("colunas", []))
        if before and (gone := before - after):
            warnings.append(f"{name}: columns removed: {', '.join(sorted(gone))}")
        if before and (added := after - before):
            rows.append(f"| `{name}.colunas` | | +{', '.join(sorted(added))} | |")

    lines = [
        "## Data manifest vs. live site",
        "",
        f"Previous build: {old.get('gerado_em', '?')} (code `{old.get('codigo_pipeline', '?')}`) · "
        f"this build: {new.get('gerado_em', '?')} (code `{new.get('codigo_pipeline', '?')}`)",
        "",
    ]
    if warnings:
        lines += [f"### ⚠ {len(warnings)} warning(s)", "", *[f"- {w}" for w in warnings], ""]
    if rows:
        lines += ["| Metric | Previous | Current | Change |", "|---|--:|--:|--:|", *rows, ""]
    lines.append(f"{unchanged} metric(s) unchanged.")
    lines += ["", "### Sources", "", "| Source | Downloaded |", "|---|---|"]
    lines += [f"| [{f['nome']}]({f['url']}) | {f['baixado_em'] or '—'} |" for f in new.get("fontes", [])]
    return "\n".join(lines) + "\n", warnings


def _load(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _publish(dist: Path) -> Path:
    """Copy Framework's content-hashed copy of the manifest to a stable URL."""
    candidates = [p for p in dist.glob("_file/**/manifest*.json") if re.fullmatch(r"manifest(\.[0-9a-f]+)?\.json", p.name)]
    if len(candidates) != 1:
        raise SystemExit(f"expected one built manifest under {dist}/_file, found {len(candidates)}: {candidates}")
    target = dist / "manifest.json"
    shutil.copyfile(candidates[0], target)
    return target


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m pipeline.manifest")
    sub = parser.add_subparsers(dest="cmd", required=True)
    pub = sub.add_parser("publish", help="copy the built manifest to dist/manifest.json")
    pub.add_argument("--dist", type=Path, default=ROOT / "dist")
    cmp_ = sub.add_parser("compare", help="report changes between two manifests")
    cmp_.add_argument("previous", type=Path)
    cmp_.add_argument("current", type=Path)
    cmp_.add_argument("--threshold", type=float, default=0.10, help="warn on drops larger than this fraction")
    cmp_.add_argument("--strict", action="store_true", help="exit 1 when there are warnings")
    args = parser.parse_args(argv)

    if args.cmd == "publish":
        print(f"manifest published at {_publish(args.dist)}")
        return 0

    new = _load(args.current)
    if new is None:
        print(f"::error::cannot read {args.current}")
        return 1
    old = _load(args.previous)
    if old is None:
        report, warnings = "## Data manifest\n\nNo previous manifest to compare with (first deploy?).\n", []
    else:
        report, warnings = compare(old, new, args.threshold)

    in_ci = os.environ.get("GITHUB_ACTIONS") == "true"
    if summary := os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(summary, "a", encoding="utf-8") as fh:
            fh.write(report)
    else:
        sys.stdout.write(report)
    if in_ci:
        for w in warnings:
            print(f"::warning title=Data regression::{w}")
    return 1 if args.strict and warnings else 0


if __name__ == "__main__":
    raise SystemExit(main())
