---
title: Falsos amigos
toc: false
---

# Falsos amigos

Palavras escritas do mesmo jeito (sem contar acentos) em duas línguas, mas com sentidos diferentes: *pain* é dor em inglês e pão em francês; *burro* é asno em espanhol e manteiga em italiano. Os sentidos são as definições do Wiktionary em inglês, como estão lá.

```js
import {parquet} from "../components/parquet.js";
import {num, resultados, rows} from "../components/format.js";
import {NOMES, ORIGENS} from "../components/poliglota.js";

const falsos = rows(await parquet(FileAttachment("../data/poliglota/falsos-amigos.parquet")));
```

```js
const filtro = view(
  Inputs.form(
    {
      a: Inputs.select(new Map([["Qualquer língua", null], ...ORIGENS.map((c) => [NOMES[c], c])]), {label: "Língua", value: "pt"}),
      b: Inputs.select(new Map([["Qualquer língua", null], ...ORIGENS.map((c) => [NOMES[c], c])]), {label: "Com"})
    },
    {template: (inputs) => html`<div class="filtros">${Object.values(inputs)}</div>`}
  )
);
```

```js
// Pairs are stored in a fixed language order; show the chosen language first.
const tem = (d, c) => !c || d.lingua_a === c || d.lingua_b === c;
const lista = falsos
  .filter((d) => tem(d, filtro.a) && tem(d, filtro.b) && (!filtro.a || !filtro.b || filtro.a !== filtro.b))
  .map((d) => {
    const virar = filtro.a && d.lingua_b === filtro.a;
    const [x, y] = virar ? ["b", "a"] : ["a", "b"];
    return {
      lingua_1: NOMES[d[`lingua_${x}`]], palavra_1: d[`palavra_${x}`], sentido_1: d[`sentido_${x}`],
      lingua_2: NOMES[d[`lingua_${y}`]], palavra_2: d[`palavra_${y}`], sentido_2: d[`sentido_${y}`],
      rank: Math.max(d.rank_a, d.rank_b)
    };
  });
const busca = view(Inputs.search(lista, {placeholder: "Buscar palavra ou sentido…", format: resultados, width: 320}));
```

```js
Inputs.table(busca, {
  columns: ["palavra_1", "lingua_1", "sentido_1", "palavra_2", "lingua_2", "sentido_2"],
  header: {palavra_1: "Palavra", lingua_1: "Em", sentido_1: "Significa", palavra_2: "Palavra", lingua_2: "Em", sentido_2: "Significa"},
  format: {sentido_1: (d) => (d?.length > 70 ? d.slice(0, 69) + "…" : d), sentido_2: (d) => (d?.length > 70 ? d.slice(0, 69) + "…" : d)},
  width: {palavra_1: 100, lingua_1: 80, palavra_2: 100, lingua_2: 80},
  rows: 20,
  select: false,
  locale: "pt-BR"
})
```

<p class="muted small">${num(busca.length)} pares, os mais comuns primeiro (ordem pela palavra mais rara do par). As duas palavras estão entre as 5.000 mais frequentes das suas línguas (no português, entre as 5.000 formas mais frequentes das legendas).</p>

<div class="note">A lista é automática e erra nas duas direções. Ficam de fora pares em que as duas definições compartilham um sentido (o espanhol <em>largar</em> e o português <em>largar</em>, "soltar"), em que uma palavra é empréstimo da outra, ou em que as duas são flexões de verbos parecidos. Ainda aparecem alguns nomes próprios e pares cujas definições dizem o mesmo com palavras diferentes.</div>

<style>
.filtros { display: flex; flex-wrap: wrap; gap: 0.5rem 1.5rem; }
.filtros form { margin: 0; }
</style>
