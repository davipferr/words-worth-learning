// Export a word selection as an Anki text import file.
//
// Anki (2.1.55+) reads "#key:value" header lines at the top of a text file:
// tab-separated, HTML fields, and a GUID column so re-importing the same list
// updates the notes instead of duplicating them. The GUIDs are derived from
// the deck GUIDs with a suffix, so a custom list never collides with notes
// imported from the ready-made .apkg decks (which use another note type).

const esc = (s) => String(s ?? "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
// Fields can't contain tabs or newlines in this format.
const campo = (s) => s.replace(/[\t\r\n]+/g, " ");

// Columns: front, back, tags, GUID. No "#columns:" labels: Anki maps labels to
// field names, and the Basic note type's fields are named per UI language
// ("Front"/"Back", "Frente"/"Verso"...), so a mismatch made it fill fields by
// position with the GUID first. With the GUID last, positional mapping is right.
const CABECALHO = ["#separator:tab", "#html:true", "#tags column:3", "#guid column:4"];

export function tsvAnki(palavras, frases, lingua) {
  const primeira = new Map(frases.filter((f) => f.lingua === lingua.codigo && f.ordem === 1).map((f) => [f.lema, f]));
  const linhas = [...CABECALHO];
  for (const p of [...palavras].sort((a, b) => a.rank - b.rank)) {
    const f = primeira.get(p.lema);
    // Example sentence in front, its translation behind, plus which word the card
    // is about. Words without an example fall back to word / definitions.
    const rodape = `<div style="opacity:.6;font-size:.8em"><b>${esc(p.lema)}</b> · nº ${p.rank} em frequência</div>`;
    let frente, verso;
    if (f) {
      frente = `<div style="font-size:1.5em">${esc(f.texto)}</div>`;
      verso = `<div style="font-size:1.5em">${esc(f.traducao)}</div>${rodape}`;
    } else {
      const defs = (p.definicao || "").split(" · ").map((g) => `<li>${esc(g)}</li>`).join("");
      frente = `<div style="font-size:2em">${esc(p.lema)}</div><div style="opacity:.6">${esc(p.classe_pt)}</div>`;
      verso = `<ol style="text-align:left">${defs}</ol>${rodape}`;
    }
    const tags = [`wwl::${lingua.codigo}`, `classe::${p.classe_pt.replace(/ /g, "_")}`].join(" ");
    linhas.push([frente, verso, tags, `${p.guid}-txt`].map(campo).join("\t"));
  }
  return linhas.join("\n") + "\n";
}

/** Download a text file built in the browser. */
export function baixar(nome, texto) {
  const url = URL.createObjectURL(new Blob([texto], {type: "text/plain;charset=utf-8"}));
  const a = Object.assign(document.createElement("a"), {href: url, download: nome});
  document.body.append(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
  return nome;
}

const LINGUAS_POLIGLOTA = [["en", "Inglês"], ["es", "Espanhol"], ["fr", "Francês"], ["it", "Italiano"], ["de", "Alemão"], ["ja", "Japonês"], ["zh", "Chinês"]];

/** Concepts as an Anki text import: Portuguese word in front, five languages behind. */
export function tsvPoliglota(conceitos) {
  const linhas = [...CABECALHO];
  for (const c of [...conceitos].sort((a, b) => a.rank_en - b.rank_en)) {
    const frente = `<div style="font-size:2em">${esc(c.palavra_pt ?? c.conceito)}</div><div style="opacity:.6">${esc(c.classe_pt)}</div>`;
    const verso = LINGUAS_POLIGLOTA.map(([code, nome]) => {
      const marca = c[`vs_pt_${code}`] && c[`vs_pt_${code}`] !== "diferente" ? ` <span style="opacity:.6;font-size:.8em">(${esc(c[`vs_pt_${code}`])})</span>` : "";
      return `<div><span style="opacity:.6">${nome}:</span> ${esc(c[`palavra_${code}`] ?? "—")}${marca}</div>`;
    }).join("");
    // Its own GUID namespace: never collides with the .apkg deck's notes.
    linhas.push([frente, verso, `wwl::poliglota classe::${c.classe_pt.replace(/ /g, "_")}`, `wwl-poli-txt-${c.conceito}-${c.classe}`].map(campo).join("\t"));
  }
  return linhas.join("\n") + "\n";
}
