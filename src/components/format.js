import * as d3 from "npm:d3";

// Brazilian number conventions: "." for thousands, "," for decimals.
export const locale = d3.formatLocale({decimal: ",", thousands: ".", grouping: [3], currency: ["", ""]});

const int = locale.format(",.0f");
const dec1 = locale.format(",.1~f"); // "1,5" but "20", not "20,0"
const pct0 = locale.format(".0%");
const pct1 = locale.format(".1%");

export const num = (x) => (x == null || Number.isNaN(x) ? "–" : int(x));
export const num1 = (x) => (x == null || Number.isNaN(x) ? "–" : dec1(x));
export const pct = (x) => (x == null || Number.isNaN(x) ? "–" : pct0(x));
export const pctd = (x) => (x == null || Number.isNaN(x) ? "–" : pct1(x));

/** Arrow table -> array of plain objects (Plot/D3 want plain objects). */
export function rows(table) {
  return Array.from(table, (r) => r.toJSON());
}

/** Result count for Inputs.search (its default label is English). */
export const resultados = (n) => (n === 0 ? "nenhum resultado" : `${int(n)} resultado${n === 1 ? "" : "s"}`);

// Fixed order everywhere (also the categorical palette slots).
export const LINGUAS = [
  {codigo: "en", nome: "Inglês"},
  {codigo: "es", nome: "Espanhol"},
  {codigo: "fr", nome: "Francês"},
  {codigo: "it", nome: "Italiano"},
  {codigo: "de", nome: "Alemão"}
];
export const nomeLingua = Object.fromEntries(LINGUAS.map((l) => [l.codigo, l.nome]));

export const GENEROS = {m: "masculino", f: "feminino", n: "neutro", "m/f": "masc. ou fem.", "f/m": "masc. ou fem."};

/** Escape a string for use inside a RegExp. */
export const escRegex = (s) => s.replace(/[.*+?^$()|[\]{}\\]/g, "\\$&");

/** The sentence as DOM nodes with the word's occurrence in bold (no innerHTML). */
export function destaque(texto, forma) {
  const span = document.createElement("span");
  if (!texto) return span;
  const re = forma ? new RegExp(`(?<![\\p{L}])${escRegex(forma)}(?![\\p{L}])`, "iu") : null;
  const m = re ? re.exec(texto) : null;
  if (!m) {
    span.textContent = texto;
    return span;
  }
  const b = document.createElement("b");
  b.textContent = m[0];
  span.append(texto.slice(0, m.index), b, texto.slice(m.index + m[0].length));
  return span;
}
