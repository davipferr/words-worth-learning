---
title: Palavras
toc: false
---

# As palavras, da mais útil para a menos útil

```js
import {parquet} from "../components/parquet.js";
import {destaque, GENEROS, LINGUAS, num, num1, pct, pctd, resultados, rows} from "../components/format.js";
import {tsvAnki, baixar} from "../components/exportar.js";

const palavras = rows(await parquet(FileAttachment("../data/palavras.parquet")));
const frases = rows(await parquet(FileAttachment("../data/frases.parquet")));
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
try {
  sessionStorage.setItem("lingua", lingua.codigo);
} catch {}
const daLingua = palavras.filter((d) => d.lingua === lingua.codigo);
const classes = d3.rollups(daLingua, (v) => v.length, (d) => d.classe_pt).sort((a, b) => b[1] - a[1]).map(([c]) => c);
```

```js
const filtros = view(
  Inputs.form(
    {
      classes: Inputs.select(classes, {label: "Classe", multiple: true, value: [], width: 220}),
      faixa: Inputs.select(new Map([["Todas (1–5.000)", [1, 5000]], ["1–500", [1, 500]], ["501–1.000", [501, 1000]], ["1.001–2.000", [1001, 2000]], ["2.001–3.000", [2001, 3000]], ["3.001–5.000", [3001, 5000]]]), {label: "Posição"}),
      frase: Inputs.toggle({label: "Só com frase de exemplo"})
    },
    {template: (inputs) => html`<div class="filtros">${Object.values(inputs)}</div>`}
  )
);
```

```js
const filtradas = daLingua.filter(
  (d) => d.rank >= filtros.faixa[0] && d.rank <= filtros.faixa[1] && (!filtros.classes.length || filtros.classes.includes(d.classe_pt)) && (!filtros.frase || d.frase)
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
            (f) => html`<p class="frase">${destaque(f.texto, f.forma)}<br><span class="muted">${f.traducao}${f.lingua_traducao === "en" ? " (inglês)" : ""}</span> <a class="small muted" href=${`https://tatoeba.org/pt-br/sentences/show/${f.frase_id}`}>Tatoeba</a></p>`
          )}`
        : html`<p class="muted">O Tatoeba não tem uma frase curta com tradução para esta palavra.</p>`}
    </div>`
  : html`<p class="muted">Nenhuma palavra com esses filtros.</p>`
```

## Levar para o Anki

As ${num(busca.length)} palavras filtradas acima podem ir para o Anki num arquivo de texto. No Anki, use **Arquivo → Importar**, escolha o tipo de nota **Básico** e um baralho. A frente do cartão tem a palavra; o verso, pronúncia, definições e frase de exemplo. Para os baralhos prontos, com leitura em voz alta, veja [Baralhos Anki](./anki).

```js
const exportar = view(Inputs.button(`Baixar ${num(busca.length)} palavras (.txt para o Anki)`, {value: null, reduce: () => baixar(`palavras-${lingua.codigo}.txt`, tsvAnki(busca, frases, lingua))}));
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
