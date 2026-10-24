---
title: Vantagem de partida
---

# Vantagem de partida

```js
import {parquet} from "../components/parquet.js";
import {num, pct, resultados, rows} from "../components/format.js";
import {palette} from "../components/palette.js";
import {ALVOS, barrasOrigem, marca, matriz, NOMES, ORIGENS} from "../components/poliglota.js";

const vantagem = rows(await parquet(FileAttachment("../data/poliglota/vantagem.parquet")));
const pares = rows(await parquet(FileAttachment("../data/poliglota/pares.parquet")));
const conceitos = rows(await parquet(FileAttachment("../data/poliglota/conceitos.parquet")));
const pal = palette(dark);
```

Se você já sabe uma língua, quanto da outra você reconhece sem estudar? Para cada palavra entre as 5.000 mais frequentes da língua que você quer aprender, buscamos a palavra equivalente na língua que você já sabe e classificamos o par:

- **igual**: mesma grafia, sem contar acentos (*casa*, *casa*);
- **parecida**: uma letra de diferença, ou pelo menos metade das letras no lugar (*noche* e *noite*, *Haus* e *house*);
- **mesma origem**: escrita diferente, mas o Wiktionary dá a ambas um ancestral comum (*hijo* e *filho*, do latim *filius*). Esse grupo é um piso, porque as etimologias do Wiktionary estão incompletas;
- **diferente**.

A vantagem é a soma das ocorrências, nas legendas, das palavras iguais ou parecidas, dividida pelo total de palavras ditas na língua.

Japonês e chinês entram de dois jeitos. Com as línguas de alfabeto latino, só contam as palavras japonesas escritas em katakana (empréstimos), comparadas pela transcrição: *パン* (pan) e *pão*, *ダンス* (dansu) e *dança*. Entre si, as duas comparam caracteres: o japonês *電話* é o chinês *電話* (tradicional) ou *电话* (simplificado). É reconhecimento na escrita, não no som. E a parcela fica baixa porque, no japonês, as palavras gramaticais (partículas, terminações de verbo) são escritas em kana, que o chinês não tem.

```js
const medida = view(
  Inputs.radio(
    new Map([
      ["Reconhecível (igual ou parecida)", "reconhecivel"],
      ["Mesma origem, outra cara", "mesma_origem"],
      ["Com equivalente alinhado", "alinhada"]
    ]),
    {label: "Medida", value: "reconhecivel"}
  )
);
```

```js
resize((width) => matriz(vantagem, {width, pal, y: medida, destaque: (d) => d.origem === "pt"}))
```

<p class="muted small">"Com equivalente alinhado": parcela do que se fala na língua da coluna cujas palavras têm um equivalente na língua da linha, seja qual for a semelhança. O que falta até 100% são palavras sem alinhamento (gírias, nomes, palavras fora das 5.000 mais frequentes do inglês, que definem os conceitos).</p>

## Qual a próxima língua?

```js
const sei = view(Inputs.checkbox(ORIGENS, {label: "Já sei", format: (d) => NOMES[d], value: ["pt"]}));
```

```js
const sugestao = ALVOS.filter((b) => !sei.includes(b))
  .map((b) => {
    const opcoes = vantagem.filter((d) => d.alvo === b && sei.includes(d.origem));
    const top = opcoes.sort((x, y) => y.reconhecivel - x.reconhecivel)[0];
    return top ? {alvo: b, reconhecivel: top.reconhecivel, via: top.origem, top1000: top.reconheciveis_top1000} : null;
  })
  .filter(Boolean)
  .sort((x, y) => y.reconhecivel - x.reconhecivel);
```

```js
sei.length === 0
  ? html`<p class="muted">Marque pelo menos uma língua.</p>`
  : sugestao.length === 0
  ? html`<p class="muted">Você já marcou todas as línguas do site.</p>`
  : Inputs.table(sugestao, {
      header: {alvo: "Próxima língua", reconhecivel: "Já reconhecível", via: "Graças a", top1000: "Das 1.000 mais comuns, reconhecíveis"},
      format: {alvo: (d) => NOMES[d], via: (d) => NOMES[d], reconhecivel: pct, top1000: num},
      sort: null,
      select: false,
      layout: "auto"
    })
```

<p class="muted small">Para cada língua, a vantagem da língua que você já sabe que mais ajuda com ela. Saber duas línguas parecidas não soma: as palavras reconhecíveis por uma em geral são as mesmas da outra.</p>

## Par a par

```js
const par = view(
  Inputs.form(
    {
      origem: Inputs.select(ORIGENS, {label: "Já sei", format: (d) => NOMES[d], value: "pt"}),
      alvo: Inputs.select(ALVOS, {label: "Quero aprender", format: (d) => NOMES[d], value: "it"})
    },
    {template: (inputs) => html`<div class="filtros">${Object.values(inputs)}</div>`}
  )
);
```

```js
resize((width) => barrasOrigem(vantagem, par.origem, {width, pal}))
```

<p class="muted small">De ${NOMES[par.origem].toLowerCase()} para cada língua: parcela do que se fala que é igual, parecida ou de mesma origem.</p>

```js
// Pairs are stored once per concept in a fixed language order; orient them as (origem, alvo).
const doPar = par.origem === par.alvo
  ? []
  : pares
      .filter((d) => (d.lingua_a === par.origem && d.lingua_b === par.alvo) || (d.lingua_a === par.alvo && d.lingua_b === par.origem))
      .map((d) => {
        const direto = d.lingua_a === par.origem;
        const c = conceitosPor.get(d.conceito);
        return {
          rank: c?.[`rank_${par.alvo}`] ?? c?.rank_en,
          alvo: direto ? d.palavra_b : d.palavra_a,
          origem: direto ? d.palavra_a : d.palavra_b,
          classe: d.classe,
          conceito: d.conceito
        };
      })
      .sort((a, b) => a.rank - b.rank);
const classeFiltro = view(Inputs.checkbox(["igual", "parecida", "mesma origem", "diferente"], {label: "Mostrar", value: ["igual", "parecida", "mesma origem", "diferente"]}));
```

```js
const conceitosPor = new Map(conceitos.map((d) => [d.conceito, d]));
```

```js
const mostrados = doPar.filter((d) => classeFiltro.includes(d.classe));
const busca = view(Inputs.search(mostrados, {placeholder: "Buscar palavra…", columns: ["alvo", "origem", "conceito"], format: resultados, width: 300}));
```

```js
Inputs.table(busca, {
  columns: ["rank", "alvo", "origem", "classe", "conceito"],
  header: {rank: "Nº", alvo: NOMES[par.alvo], origem: NOMES[par.origem], classe: "Semelhança", conceito: "Conceito (inglês)"},
  format: {rank: num, classe: (d) => marca(d, pal)},
  width: {rank: 60},
  sort: "rank",
  rows: 16,
  select: false,
  locale: "pt-BR"
})
```

<p class="muted small">Nº: posição da palavra em frequência na língua que você quer aprender. ${par.origem === par.alvo ? "Escolha duas línguas diferentes." : ""}</p>

<style>
.filtros { display: flex; flex-wrap: wrap; gap: 0.5rem 1.5rem; }
.filtros form { margin: 0; }
.marca { font-size: 12px; border: 1px solid; border-radius: 999px; padding: 0 0.45rem; white-space: nowrap; }
</style>
