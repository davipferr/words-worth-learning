import * as Plot from "npm:@observablehq/plot";
import {pct} from "./format.js";

export const NOMES = {pt: "Português", en: "Inglês", es: "Espanhol", fr: "Francês", it: "Italiano", de: "Alemão", ja: "Japonês", zh: "Chinês"};
export const ORIGENS = ["pt", "en", "es", "fr", "it", "de", "ja", "zh"];
export const ALVOS = ["en", "es", "fr", "it", "de", "ja", "zh"];
export const CLASSES = ["igual", "parecida", "mesma origem", "diferente"];

/** Class colours: the two "recognisable" classes in strong hues, the rest muted. */
export function corClasse(pal) {
  return {igual: pal.categorical[2], parecida: pal.categorical[0], "mesma origem": pal.categorical[3], diferente: pal.muted};
}

/** Small coloured label for a word's class against another language. */
export function marca(classe, pal) {
  const span = document.createElement("span");
  if (!classe) return span;
  if (classe === "diferente") {
    span.className = "muted small";
    span.textContent = "diferente";
    return span;
  }
  span.className = "marca";
  span.textContent = classe;
  span.style.borderColor = corClasse(pal)[classe];
  span.style.color = corClasse(pal)[classe];
  return span;
}

/**
 * The advantage matrix as a heatmap: rows are the language you know, columns
 * the one you want to learn, cells the share of what is said in the column
 * language that is recognisable from the row language.
 */
export function matriz(vantagem, {width, pal, y = "reconhecivel", destaque}) {
  // Phones: language codes instead of names, so five columns fit in ~340 px.
  const narrow = width < 480;
  const nome = (d) => (narrow ? d.toUpperCase() : NOMES[d]);
  const left = narrow ? 52 : 100;
  const cell = Math.min(96, Math.max(narrow ? 40 : 54, (width - left - 10) / ALVOS.length));
  const max = Math.max(...vantagem.map((d) => d[y]));
  return Plot.plot({
    width: Math.min(width, left + 10 + cell * ALVOS.length),
    height: 40 + cell * 0.62 * ORIGENS.length,
    marginLeft: left,
    marginTop: 34,
    padding: 0.06,
    style: {fontSize: narrow ? "11px" : "12px"},
    x: {domain: ALVOS, tickFormat: nome, axis: "top", label: narrow ? "Quero aprender (%) →" : "Quero aprender →", tickSize: 0},
    y: {domain: ORIGENS, tickFormat: (d) => (d === "pt" ? `${nome(d)} ★` : nome(d)), label: "Já sei ↓", tickSize: 0},
    color: {type: "linear", domain: [0, max], range: pal.blues(2), legend: false},
    marks: [
      // Plot drops marks whose channel value is null, so "no outline" must be "none".
      Plot.cell(vantagem, {x: "alvo", y: "origem", fill: y, rx: 4, stroke: (d) => (destaque && destaque(d) ? "currentColor" : "none"), strokeWidth: 2}),
      // Dark-only site: the ramp runs dark -> light, so strong cells get dark text.
      // Phones: bare numbers (the caption says they are percentages), smaller.
      Plot.text(vantagem, {
        x: "alvo",
        y: "origem",
        text: (d) => (narrow ? String(Math.round(d[y] * 100)) : pct(d[y])),
        fill: (d) => (d[y] > max * 0.55 ? "#111" : "currentColor"),
        fontSize: narrow ? 11 : 13,
        fontWeight: 600
      }),
      Plot.tip(
        vantagem,
        Plot.pointer({
          x: "alvo",
          y: "origem",
          title: (d) =>
            `Sabendo ${NOMES[d.origem].toLowerCase()}, em ${NOMES[d.alvo].toLowerCase()}:\n${pct(d.reconhecivel)} do que se fala é reconhecível\n(${pct(d.igual)} igual, ${pct(d.parecida)} parecido)\n${pct(d.mesma_origem)} tem a mesma origem, mas outra cara\n${d.reconheciveis_top1000} das 1.000 palavras mais comuns são reconhecíveis`
        })
      )
    ]
  });
}

/** Stacked bar per target language for one starting language: igual / parecida / mesma origem. */
export function barrasOrigem(vantagem, origem, {width, pal}) {
  const cor = corClasse(pal);
  const rows = vantagem
    .filter((d) => d.origem === origem)
    .flatMap((d) => [
      {alvo: d.alvo, classe: "igual", v: d.igual},
      {alvo: d.alvo, classe: "parecida", v: d.parecida},
      {alvo: d.alvo, classe: "mesma origem", v: d.mesma_origem}
    ]);
  const ordem = vantagem.filter((d) => d.origem === origem).sort((a, b) => b.reconhecivel - a.reconhecivel).map((d) => d.alvo);
  return Plot.plot({
    width,
    height: ordem.length * 34 + 40,
    marginLeft: 80,
    x: {tickFormat: pct, label: "Parcela do que se fala na língua →", grid: true, domain: [0, 0.8]},
    y: {domain: ordem, tickFormat: (d) => NOMES[d], label: null, tickSize: 0},
    color: {domain: ["igual", "parecida", "mesma origem"], range: [cor.igual, cor.parecida, cor["mesma origem"]], legend: true},
    marks: [Plot.barX(rows, {x: "v", y: "alvo", fill: "classe", order: ["igual", "parecida", "mesma origem"], tip: {format: {x: pct}}}), Plot.ruleX([0])]
  });
}
