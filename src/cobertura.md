---
title: Cobertura
---

# Quantas palavras são suficientes?

```js
import {parquet} from "./components/parquet.js";
import {LINGUAS, num, pct, pctd, rows} from "./components/format.js";
import {palette} from "./components/palette.js";
import {curvas, ganhos, legenda} from "./components/charts.js";

const cobertura = rows(await parquet(FileAttachment("data/cobertura.parquet")));
const resumo = await FileAttachment("data/resumo.json").json();
```

```js
const pal = palette(dark);
const linguas = LINGUAS.filter((l) => resumo.linguas.some((r) => r.codigo === l.codigo));
const porCodigo = Object.fromEntries(resumo.linguas.map((r) => [r.codigo, r]));
```

A curva de cobertura responde: se você souber as N palavras mais frequentes de uma língua, que parcela das palavras ditas num filme ou série você reconhece? As primeiras palavras rendem muito — artigos, pronomes, "ser", "ter" —, e cada nova palavra rende menos que a anterior.

${legenda(pal, linguas)}

```js
resize((width) => curvas(cobertura, {width, pal, linguas, alvo: 0.9}))
```

<p class="muted small">Eixo horizontal em escala logarítmica. A cobertura é a soma das ocorrências das N palavras (com todas as suas formas) dividida pelo total de palavras das legendas.</p>

## Palavras necessárias por meta

```js
Inputs.table(
  linguas.map((l) => {
    const r = porCodigo[l.codigo];
    // Inputs.table skips the formatter for null, so "out of range" is spelled out here.
    return {lingua: l.nome, p50: r.para["50"], p80: r.para["80"], p90: r.para["90"], p95: r.para["95"] ?? "mais de 10.000", c1000: r.cobertura_em["1000"], c5000: r.cobertura_em["5000"]};
  }),
  {
    header: {lingua: "Língua", p50: "50%", p80: "80%", p90: "90%", p95: "95%", c1000: "Com 1.000", c5000: "Com 5.000"},
    format: {p50: num, p80: num, p90: num, p95: (d) => (typeof d === "string" ? d : num(d)), c1000: pct, c5000: pct},
    sort: null,
    select: false,
    layout: "auto"
  }
)
```

<p class="muted small">Colunas 50% a 95%: quantas palavras, das mais frequentes para as menos, são necessárias para reconhecer essa parcela do que se fala. As duas últimas colunas fazem a conta inversa.</p>

Pesquisas sobre leitura costumam citar 95% a 98% de palavras conhecidas como o limiar para entender um texto sem esforço. Nas legendas, a fala do dia a dia, a cobertura sobe rápido: o italiano é a língua que mais exige, por ter mais formas por verbo e mais palavras distintas.

## Cada faixa rende menos que a anterior

```js
resize((width) => ganhos(cobertura, {width, pal, linguas, faixas: [[1, 100], [101, 500], [501, 1000], [1001, 2000], [2001, 5000], [5001, 10000]]}))
```

<p class="muted small">Quantos pontos percentuais de cobertura cada faixa acrescenta. As 100 primeiras palavras sozinhas cobrem mais da metade do que se fala; as 5.000 da última faixa juntas acrescentam poucos pontos.</p>

## Aprender palavras, não formas

As listas de frequência contam *formas*: "estoy", "estaba" e "estuvo" aparecem separadas. Agrupá-las por palavra de dicionário (o *lema*, aqui "estar") faz cada item estudado valer mais, porque uma conjugação ajuda a reconhecer as outras:

```js
const qual = view(Inputs.radio(linguas, {label: "Língua", format: (l) => l.nome, value: linguas[0]}));
```

```js
resize((width) =>
  Plot.plot({
    width,
    height: 320,
    marginLeft: 44,
    marginBottom: 36,
    x: {type: "log", domain: [1, 10000], ticks: [1, 10, 100, 1000, 10000], tickFormat: num, label: "Itens aprendidos →", grid: true},
    y: {domain: [0, 1], tickFormat: pct, label: "↑ Cobertura", grid: true},
    color: {domain: ["Palavras (lemas)", "Formas, uma a uma"], range: [pal.accent, pal.muted], legend: true},
    marks: [
      Plot.line(cobertura.filter((d) => d.lingua === qual.codigo), {x: "rank", y: "cobertura", stroke: () => "Palavras (lemas)", strokeWidth: 2}),
      Plot.line(cobertura.filter((d) => d.lingua === qual.codigo), {x: "rank", y: "cobertura_formas", stroke: () => "Formas, uma a uma", strokeWidth: 2, strokeDasharray: "5 3"}),
      Plot.tip(cobertura.filter((d) => d.lingua === qual.codigo), Plot.pointerX({x: "rank", y: "cobertura", title: (d) => `${num(d.rank)} itens\npalavras: ${pctd(d.cobertura)}\nformas: ${pctd(d.cobertura_formas)}`}))
    ]
  })
)
```

```js
const q = porCodigo[qual.codigo];
```

Em ${qual.nome.toLowerCase()}, ${num(q.para["80"])} palavras cobrem 80% do que se fala; aprendendo formas soltas seriam necessárias ${num(q.formas_para["80"])}.

## O que fica de fora

```js
Inputs.table(
  linguas.map((l) => ({lingua: l.nome, ...porCodigo[l.codigo].parcela})),
  {
    header: {lingua: "Língua", palavras: "Palavras do dicionário", nomes: "Nomes próprios", fora: "Fora do dicionário"},
    format: {palavras: pctd, nomes: pctd, fora: pctd},
    sort: null,
    select: false,
    layout: "auto"
  }
)
```

<p class="muted small">Parcela de todas as palavras das legendas. "Fora do dicionário" junta erros de digitação, gírias raras, interjeições como "hmm", trechos em outras línguas e palavras que o Wiktionary não registra. Essa parte nunca entra na cobertura, então as curvas não chegam a 100%.</p>
