import * as Plot from "npm:@observablehq/plot";
import {LINGUAS, nomeLingua, num, pct} from "./format.js";

/** Colour of each language: fixed palette slot by its position in LINGUAS. */
export function corLingua(pal) {
  return Object.fromEntries(LINGUAS.map((l, i) => [l.codigo, pal.categorical[i]]));
}

const TICKS = [1, 10, 100, 1000, 10000];

/**
 * Coverage curves: share of everything said in subtitles covered by the top N
 * words, one line per language, on a log x axis (the first hundred words do
 * most of the work). Optional horizontal guide at `alvo` (e.g. 0.9).
 */
export function curvas(data, {width, pal, linguas, y = "cobertura", alvo, height = 360}) {
  const cor = corLingua(pal);
  const codigos = linguas.map((l) => l.codigo);
  const rows = data.filter((d) => codigos.includes(d.lingua) && d[y] != null);
  // The lines converge at the right end, so the legend above names them, not end labels.
  return Plot.plot({
    width,
    height,
    marginLeft: 44,
    marginRight: 16,
    marginBottom: 36,
    x: {type: "log", domain: [1, 10000], ticks: TICKS, tickFormat: num, label: "Palavras aprendidas, das mais frequentes para as menos →", grid: true},
    y: {domain: [0, 1], tickFormat: pct, label: "↑ Do que se fala, quanto você reconhece", grid: true},
    color: {domain: codigos, range: codigos.map((c) => cor[c])},
    marks: [
      alvo ? Plot.ruleY([alvo], {stroke: "currentColor", strokeOpacity: 0.35, strokeDasharray: "4 3"}) : null,
      Plot.line(rows, {x: "rank", y, stroke: "lingua", strokeWidth: 2}),
      Plot.tip(
        rows,
        Plot.pointer({
          x: "rank",
          y,
          stroke: "lingua",
          channels: {Língua: (d) => nomeLingua[d.lingua], Palavras: (d) => num(d.rank), Cobertura: (d) => pct(d[y])},
          format: {x: false, y: false, stroke: false}
        })
      )
    ]
  });
}

/** Legend row (swatch + language name) for the curves above. */
export function legenda(pal, linguas) {
  const cor = corLingua(pal);
  const div = document.createElement("div");
  div.className = "legend-row";
  for (const l of linguas) {
    const span = document.createElement("span");
    const i = document.createElement("i");
    i.style.background = cor[l.codigo];
    span.append(i, l.nome);
    div.append(span);
  }
  return div;
}

/** How many percentage points each band of words adds, per language. */
export function ganhos(data, {width, pal, linguas, faixas}) {
  const cor = corLingua(pal);
  const rows = [];
  for (const l of linguas) {
    const curva = new Map(data.filter((d) => d.lingua === l.codigo).map((d) => [d.rank, d.cobertura]));
    for (const [a, b] of faixas) {
      const ini = a === 1 ? 0 : curva.get(a - 1);
      const fim = curva.get(b);
      if (ini != null && fim != null) rows.push({lingua: l.codigo, faixa: `${num(a)}–${num(b)}`, ganho: fim - ini});
    }
  }
  const pp = (d) => `+${(d * 100).toLocaleString("pt-BR", {maximumFractionDigits: 1})} p.p.`;
  // Grouped columns: one facet per band, one column per language inside it.
  return Plot.plot({
    width,
    height: 300,
    marginLeft: 48,
    marginBottom: 36,
    fx: {domain: faixas.map(([a, b]) => `${num(a)}–${num(b)}`), label: "Faixa de palavras, por frequência", padding: 0.12},
    x: {axis: null, domain: linguas.map((l) => l.codigo), padding: 0.1},
    y: {tickFormat: (d) => `${Math.round(d * 100)} p.p.`, label: "↑ Cobertura que a faixa acrescenta", grid: true},
    color: {domain: linguas.map((l) => l.codigo), range: linguas.map((l) => cor[l.codigo])},
    marks: [
      Plot.barY(rows, {fx: "faixa", x: "lingua", y: "ganho", fill: "lingua", ry2: 2, title: (d) => `${nomeLingua[d.lingua]} · palavras ${d.faixa}: ${pp(d.ganho)}`}),
      Plot.ruleY([0])
    ]
  });
}
