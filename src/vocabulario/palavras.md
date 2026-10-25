---
title: Palavras
toc: false
---

# As palavras, da mais útil para a menos útil

```js
import {parquet} from "../components/parquet.js";
import {destaque, GENEROS, LINGUAS, num, num1, pct, pctd, resultados, rows} from "../components/format.js";
import {tsvAnki, baixar, frasesDosCartoes, traducao} from "../components/exportar.js";

const palavras = rows(await parquet(FileAttachment("../data/palavras.parquet")));
const frases = rows(await parquet(FileAttachment("../data/frases.parquet")));
const resumo = await FileAttachment("../data/resumo.json").json();
```

```js
const disponiveis = LINGUAS.filter((l) => palavras.some((d) => d.lingua === l.codigo));
let lembrada;
try {
  lembrada = sessionStorage.getItem("lingua");
} catch {}
const lingua = view(
  Inputs.radio(disponiveis, {label: "Língua", format: (l) => l.nome, value: disponiveis.find((l) => l.codigo === lembrada) ?? disponiveis[0]})
);
```

```js
// The language example sentences are translated into: Portuguese, or another
// language to study one through the other (Spanish through English…).
const LINGUAS_TRADUCAO = [{codigo: "pt", nome: "Português"}, ...LINGUAS];
let lembradaTraducao;
try {
  lembradaTraducao = sessionStorage.getItem("traducao");
} catch {}
const traducaoEm = view(
  Inputs.select(LINGUAS_TRADUCAO, {label: "Tradução das frases", format: (l) => l.nome, value: LINGUAS_TRADUCAO.find((l) => l.codigo === lembradaTraducao) ?? LINGUAS_TRADUCAO[0]})
);
```

```js
aviso()
```

```js
try {
  sessionStorage.setItem("lingua", lingua.codigo);
  sessionStorage.setItem("traducao", traducaoEm.codigo);
} catch {}
const daLingua = palavras.filter((d) => d.lingua === lingua.codigo);
const classes = d3.rollups(daLingua, (v) => v.length, (d) => d.classe_pt).sort((a, b) => b[1] - a[1]).map(([c]) => c);
// Coverage goals from the Cobertura page; the list stops at 5.000, so a goal past it shows the whole list.
const maximo = resumo.palavras_por_lingua;
const para = resumo.linguas.find((r) => r.codigo === lingua.codigo)?.para ?? {};
const metas = ["50", "80", "90"].map((m) => {
  const n = para[m];
  const rotulo = n != null && n <= maximo ? `Meta ${m}% (1–${num(n)})` : `Meta ${m}% (1–${num(maximo)}; precisaria de ${n == null ? "mais de 10.000" : num(n)})`;
  return [rotulo, [1, Math.min(n ?? maximo, maximo)]];
});
```

```js
const filtros = view(
  Inputs.form(
    {
      // "Selecione" (null) means every class, and picking it again clears the filter.
      classe: Inputs.select([null, ...classes], {label: "Classe", format: (c) => c ?? "Selecione"}),
      faixa: Inputs.select(new Map([["Todas (1–5.000)", [1, 5000]], ...metas, ["1–500", [1, 500]], ["501–1.000", [501, 1000]], ["1.001–2.000", [1001, 2000]], ["2.001–3.000", [2001, 3000]], ["3.001–5.000", [3001, 5000]]]), {label: "Posição"}),
      frase: Inputs.toggle({label: "Só com frase de exemplo"})
    },
    {template: (inputs) => html`<div class="filtros">${Object.values(inputs)}</div>`}
  )
);
```

```js
const filtradas = daLingua.filter(
  (d) => d.rank >= filtros.faixa[0] && d.rank <= filtros.faixa[1] && (!filtros.classe || d.classe_pt === filtros.classe) && (!filtros.frase || d.frase)
);
const busca = view(Inputs.search(filtradas, {placeholder: "Buscar palavra ou definição…", columns: ["lema", "formas", "definicao"], format: resultados, width: 340}));
```

```js
const escolhida = view(
  Inputs.table(busca, {
    columns: ["rank", "lema", "classe_pt", "ipa", "definicao", "por_milhao", "cobertura"],
    header: {rank: "Nº", lema: "Palavra", classe_pt: "Classe", ipa: "Pronúncia", definicao: "Definição (Wiktionary)", por_milhao: "Por milhão", cobertura: "Cobertura até aqui"},
    format: {rank: num, por_milhao: num1, cobertura: pctd, definicao: (d) => (d && d.length > 90 ? d.slice(0, 89) + "…" : d)},
    width: {rank: 56, lema: 130, classe_pt: 110, ipa: 120, por_milhao: 90, cobertura: 90},
    sort: "rank",
    rows: 16,
    multiple: false,
    required: false,
    locale: "pt-BR"
  })
);
```

<p class="muted small">Clique numa linha para ver a palavra. "Por milhão": quantas vezes a palavra (com todas as formas) aparece a cada milhão de palavras das legendas. "Cobertura até aqui": parcela do que se fala coberta por esta palavra e todas as mais frequentes que ela.</p>

```js
const p = escolhida ?? busca[0];
const exemplos = p ? frases.filter((f) => f.lingua === p.lingua && f.lema === p.lema) : [];
```

```js
p
  ? html`<div class="card palavra">
      <div class="cabeca">
        <h2>${p.lema}</h2>
        <span class="muted">${p.classe_pt}${p.genero ? `, ${GENEROS[p.genero] ?? p.genero}` : ""}${p.ipa ? html` · <span class="ipa">${p.ipa}</span>` : ""}</span>
        <span class="muted small">nº ${num(p.rank)} em frequência · ${num1(p.por_milhao)} por milhão</span>
      </div>
      <ol class="definicoes">${p.definicao.split(" · ").map((g) => html`<li>${g}</li>`)}</ol>
      ${p.formas ? html`<p class="small"><strong>Formas mais comuns:</strong> ${p.formas}</p>` : ""}
      ${p.etimo ? html`<p class="small muted"><strong>Etimologia:</strong> ${p.etimo}.</p>` : ""}
      ${exemplos.length
        ? html`<h3>Frases de exemplo</h3>${exemplos.map(
            (f) => html`<p class="frase">${destaque(f.texto, f.forma)}<br><span class="muted">${traducao(f, traducaoEm.codigo) ?? html`<i>sem tradução em ${traducaoEm.nome} no Tatoeba</i>`}</span> <a class="small muted" href=${`https://tatoeba.org/pt-br/sentences/show/${f.frase_id}`}>Tatoeba</a></p>`
          )}`
        : html`<p class="muted">O Tatoeba não tem uma frase curta com tradução para esta palavra.</p>`}
    </div>`
  : html`<p class="muted">Nenhuma palavra com esses filtros.</p>`
```

## Levar para o Anki

As ${num(busca.length)} palavras filtradas acima podem ir para o Anki num arquivo de texto. No Anki, use **Arquivo → Importar**, escolha o tipo de nota **Básico** e um baralho. A frente do cartão tem uma frase de exemplo com a palavra; o verso, a tradução da frase (na língua escolhida em **Tradução das frases**, no alto da página) e a palavra em destaque com sua posição em frequência. Quando o Tatoeba não tem a frase traduzida nessa língua, o verso mostra *(without translation)*, para você procurar a tradução. Palavras sem nenhuma frase de exemplo ficam com a palavra na frente e as definições no verso. Para os baralhos prontos, com leitura em voz alta, veja [Baralhos Anki](./anki).

```js
const doCartao = frasesDosCartoes(frases, lingua, traducaoEm.codigo);
// Words whose card sentence has no translation in the chosen language.
const semTraducao = busca.filter((d) => doCartao.has(d.lema) && !traducao(doCartao.get(d.lema), traducaoEm.codigo)).length;
// Shown here and under the "Tradução das frases" select; a function because a
// DOM node can only be in one place. Always an element (an empty one when all is
// well): a block that displays nothing keeps showing its previous output.
const aviso = () =>
  traducaoEm.codigo === lingua.codigo
    ? html`<div class="warning">As frases de exemplo já estão em ${lingua.nome}, e o Tatoeba não traduz uma frase para a própria língua: nenhuma frase terá tradução. No Anki, o verso dos cartões com frase mostra "(without translation)".</div>`
    : semTraducao
      ? html`<div class="warning">${num(semTraducao)} das ${num(busca.length)} palavras filtradas têm frase de exemplo sem tradução em ${traducaoEm.nome} no Tatoeba. No Anki, o verso delas mostra "(without translation)".</div>`
      : html`<span></span>`;
```

```js
aviso()
```

```js
const exportar = view(Inputs.button(`Baixar ${num(busca.length)} palavras (.txt para o Anki)`, {value: null, reduce: () => baixar(`palavras-${lingua.codigo}-${traducaoEm.codigo}.txt`, tsvAnki(busca, frases, lingua, traducaoEm.codigo))}));
```

<p class="muted small">O arquivo usa os cabeçalhos de importação do Anki (2.1.55 ou mais novo, ou AnkiDroid 2.17+): campos em HTML, separados por tabulação, e um identificador fixo por palavra. Importar de novo uma lista que já foi importada atualiza os cartões existentes em vez de duplicá-los.</p>

<style>
.filtros { display: flex; flex-wrap: wrap; gap: 0.5rem 1.5rem; align-items: flex-start; }
.filtros form { margin: 0; }
.palavra .cabeca { display: flex; flex-wrap: wrap; align-items: baseline; gap: 0.25rem 1rem; }
.palavra h2 { font: 600 32px/1.1 var(--serif); margin: 0; }
.ipa { color: var(--theme-foreground-focus); }
.definicoes { max-width: 48rem; padding-left: 1.3rem; }
.frase { margin: 0.4rem 0 0.8rem; max-width: 48rem; }
.frase b { color: var(--theme-foreground-focus); }
</style>
