---
title: Consulta SQL
---

# Consulta SQL no navegador

Os arquivos Parquet que alimentam o site são carregados num **DuckDB rodando no seu navegador** (DuckDB-WASM). Nada é enviado a servidor algum — monte as suas próprias listas.

```js
import {parquet} from "./components/parquet.js";
// Tables are decoded to Arrow first (parquet-wasm, the same reader the other pages
// use) and copied into DuckDB, instead of letting DuckDB-WASM read the Parquet files
// itself. That avoids two problems: its HTTP range requests break on GitHub Pages,
// which gzips .parquet responses, and its bundled DuckDB 1.1 can't parse the footer
// of files written by Polars 2.
const db = DuckDBClient.of({
  palavras: parquet(FileAttachment("data/palavras.parquet")),
  frases: parquet(FileAttachment("data/frases.parquet")),
  cobertura: parquet(FileAttachment("data/cobertura.parquet")),
  conceitos: parquet(FileAttachment("data/poliglota/conceitos.parquet")),
  pares: parquet(FileAttachment("data/poliglota/pares.parquet")),
  vantagem: parquet(FileAttachment("data/poliglota/vantagem.parquet")),
  falsos_amigos: parquet(FileAttachment("data/poliglota/falsos-amigos.parquet"))
});
```

```js
const exemplos = new Map([
  ["Os 30 verbos mais frequentes do espanhol", `SELECT rank, lema, ipa, definicao
FROM palavras
WHERE lingua = 'es' AND classe = 'verb'
ORDER BY rank
LIMIT 30`],
  ["Quantas palavras para 90% em cada língua", `SELECT lingua, min(rank) AS palavras
FROM cobertura
WHERE cobertura >= 0.9
GROUP BY lingua
ORDER BY palavras`],
  ["Classes de palavra entre as 1.000 primeiras", `SELECT lingua, classe_pt, count(*) AS n
FROM palavras
WHERE rank <= 1000
GROUP BY lingua, classe_pt
QUALIFY row_number() OVER (PARTITION BY lingua ORDER BY count(*) DESC) <= 4
ORDER BY lingua, n DESC`],
  ["Palavras com mais formas diferentes nas legendas", `SELECT lingua, lema, n_formas, formas
FROM palavras
WHERE rank <= 2000
ORDER BY n_formas DESC
LIMIT 20`],
  ["Substantivos iguais nas línguas românicas e no português", `SELECT rank_en, palavra_pt, palavra_es, palavra_fr, palavra_it
FROM conceitos
WHERE classe = 'noun'
  AND vs_pt_es = 'igual' AND vs_pt_it = 'igual'
ORDER BY rank_en
LIMIT 40`],
  ["Vantagem a partir do português", `SELECT alvo, round(reconhecivel * 100, 1) AS reconhecivel_pct,
       round(mesma_origem * 100, 1) AS mesma_origem_pct, reconheciveis_top1000
FROM vantagem
WHERE origem = 'pt'
ORDER BY reconhecivel DESC`],
  ["Frases mais fáceis para as palavras 1.001–1.100 do alemão", `SELECT f.rank, f.lema, f.texto, f.traducao, f.dificuldade
FROM frases f
WHERE f.lingua = 'de' AND f.ordem = 1 AND f.rank BETWEEN 1001 AND 1100
ORDER BY f.rank`]
]);
const exemplo = view(Inputs.select(exemplos, {label: "Exemplo"}));
```

```js
const consulta = view(Inputs.textarea({value: exemplo, rows: 10, submit: "Executar", spellcheck: false, monospace: true, width: "100%"}));
```

```js
// DuckDB returns BIGINT/HUGEINT (e.g. count(*)) as JavaScript BigInt; convert to
// Number so formatting and charts work.
const resultado = await db.query(consulta).then(
  (r) => ({rows: Array.from(r, (row) => Object.fromEntries(Object.entries(row).map(([k, v]) => [k, typeof v === "bigint" ? Number(v) : v])))}),
  (error) => ({error})
);
```

${resultado.error ? html`<div class="caution"><strong>Erro:</strong> <code>${resultado.error.message}</code></div>` : html`<p class="muted">${resultado.rows.length.toLocaleString("pt-BR")} linhas</p>`}

```js
resultado.error ? null : Inputs.table(resultado.rows, {rows: 20, locale: "pt-BR"})
```

## Tabelas disponíveis

```js
const esquema = await Promise.all(
  ["palavras", "frases", "cobertura", "conceitos", "pares", "vantagem", "falsos_amigos"].map(async (t) => ({
    tabela: t,
    linhas: Number(Array.from(await db.query(`SELECT count(*) AS n FROM ${t}`))[0].n),
    colunas: Array.from(await db.query(`DESCRIBE ${t}`), (c) => `${c.column_name} (${c.column_type.toLowerCase()})`).join(", ")
  }))
);
```

```js
Inputs.table(esquema, {format: {linhas: (n) => n.toLocaleString("pt-BR")}, width: {tabela: 110, linhas: 80}, layout: "auto"})
```

<div class="tip"><code>lingua</code> é o código de duas letras (<code>en</code>, <code>es</code>, <code>fr</code>, <code>it</code>, <code>de</code>). <code>classe</code> usa os códigos do Wiktionary (<code>noun</code>, <code>verb</code>, <code>adj</code>…); <code>classe_pt</code> é o nome em português. Em <code>frases</code>, <code>ordem = 1</code> é a frase que vai para o cartão do Anki e <code>dificuldade</code> é a posição da palavra mais rara da frase (fora a própria palavra).</div>
