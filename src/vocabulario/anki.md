---
title: Baralhos Anki
---

# Baralhos para o Anki

```js
import {parquet} from "../components/parquet.js";
import {destaque, GENEROS, LINGUAS, num, rows} from "../components/format.js";

const resumo = await FileAttachment("../data/resumo.json").json();
const palavras = rows(await parquet(FileAttachment("../data/palavras.parquet")));
```

O [Anki](https://apps.ankiweb.net) é um aplicativo gratuito de cartões com repetição espaçada: ele mostra cada cartão logo antes de você esquecê-lo. Cada língua tem ${num(resumo.palavras_por_lingua)} palavras em baralhos por faixa de frequência. Comece pela primeira faixa: os cartões novos aparecem na ordem de frequência.

```js
// FileAttachment names must be literal, so every deck is listed here; they
// are extracted on demand from data/decks.zip (built by src/data/decks.zip.py).
const arquivos = {
  "en-0001-0500.apkg": FileAttachment("../data/decks/en-0001-0500.apkg"),
  "en-0501-1000.apkg": FileAttachment("../data/decks/en-0501-1000.apkg"),
  "en-1001-2000.apkg": FileAttachment("../data/decks/en-1001-2000.apkg"),
  "en-2001-3000.apkg": FileAttachment("../data/decks/en-2001-3000.apkg"),
  "en-3001-5000.apkg": FileAttachment("../data/decks/en-3001-5000.apkg"),
  "es-0001-0500.apkg": FileAttachment("../data/decks/es-0001-0500.apkg"),
  "es-0501-1000.apkg": FileAttachment("../data/decks/es-0501-1000.apkg"),
  "es-1001-2000.apkg": FileAttachment("../data/decks/es-1001-2000.apkg"),
  "es-2001-3000.apkg": FileAttachment("../data/decks/es-2001-3000.apkg"),
  "es-3001-5000.apkg": FileAttachment("../data/decks/es-3001-5000.apkg"),
  "fr-0001-0500.apkg": FileAttachment("../data/decks/fr-0001-0500.apkg"),
  "fr-0501-1000.apkg": FileAttachment("../data/decks/fr-0501-1000.apkg"),
  "fr-1001-2000.apkg": FileAttachment("../data/decks/fr-1001-2000.apkg"),
  "fr-2001-3000.apkg": FileAttachment("../data/decks/fr-2001-3000.apkg"),
  "fr-3001-5000.apkg": FileAttachment("../data/decks/fr-3001-5000.apkg"),
  "it-0001-0500.apkg": FileAttachment("../data/decks/it-0001-0500.apkg"),
  "it-0501-1000.apkg": FileAttachment("../data/decks/it-0501-1000.apkg"),
  "it-1001-2000.apkg": FileAttachment("../data/decks/it-1001-2000.apkg"),
  "it-2001-3000.apkg": FileAttachment("../data/decks/it-2001-3000.apkg"),
  "it-3001-5000.apkg": FileAttachment("../data/decks/it-3001-5000.apkg"),
  "de-0001-0500.apkg": FileAttachment("../data/decks/de-0001-0500.apkg"),
  "de-0501-1000.apkg": FileAttachment("../data/decks/de-0501-1000.apkg"),
  "de-1001-2000.apkg": FileAttachment("../data/decks/de-1001-2000.apkg"),
  "de-2001-3000.apkg": FileAttachment("../data/decks/de-2001-3000.apkg"),
  "de-3001-5000.apkg": FileAttachment("../data/decks/de-3001-5000.apkg")
};
const linguas = LINGUAS.filter((l) => resumo.linguas.some((r) => r.codigo === l.codigo));
```

```js
html`<div class="grid grid-cols-${Math.min(linguas.length, 3)}">${linguas.map((l) => {
  const r = resumo.linguas.find((d) => d.codigo === l.codigo);
  return html`<div class="card baralhos">
    <h2>${l.nome}</h2>
    <ul>${r.baralhos.map(
      (b) => html`<li><a href=${arquivos[b.arquivo].href} download=${b.arquivo}>Palavras ${num(b.de)}–${num(b.ate)}</a> <span class="muted small">${num(b.ate - b.de + 1)} cartões</span></li>`
    )}</ul>
    <p class="muted small">Com as 500 primeiras você reconhece ${Math.round(r.cobertura_em["500"] * 100)}% do que se fala; com as 5.000, ${Math.round(r.cobertura_em["5000"] * 100)}%.</p>
  </div>`;
})}</div>`
```

## Como importar

1. Instale o Anki no computador ([apps.ankiweb.net](https://apps.ankiweb.net)) ou o AnkiDroid no Android. No iPhone, o AnkiMobile é pago.
2. Baixe um baralho acima e abra o arquivo `.apkg`, ou use **Arquivo → Importar** no Anki.
3. Os baralhos aparecem como *Palavras que valem a pena › Língua › faixa*. Estude a faixa 1–500 primeiro.

## O cartão

A frente mostra a palavra e a classe, e o Anki a lê em voz alta com as vozes do seu sistema (o recurso `{{tts}}` do Anki; nenhum áudio vem no arquivo). O verso traz a pronúncia em IPA, as definições do Wiktionary como estão escritas lá, uma frase de exemplo do Tatoeba com tradução e as formas mais comuns da palavra.

```js
const lingua = view(Inputs.radio(linguas, {label: "Exemplo em", format: (l) => l.nome, value: linguas.find((l) => l.codigo === "es") ?? linguas[0]}));
```

```js
const ex = palavras.filter((d) => d.lingua === lingua.codigo && d.frase).sort((a, b) => a.rank - b.rank)[40];
```

```js
html`<div class="cartoes">
  <div class="cartao"><div class="rotulo">Frente</div>
    <div class="c-palavra">${ex.lema}</div><div class="c-classe">${ex.classe_pt}</div><div class="c-som">🔊 lida em voz alta</div>
  </div>
  <div class="cartao"><div class="rotulo">Verso</div>
    <div class="c-palavra">${ex.lema}</div><div class="c-classe">${ex.classe_pt}${ex.genero ? `, ${GENEROS[ex.genero] ?? ex.genero}` : ""}</div>
    <hr>
    ${ex.ipa ? html`<div class="c-ipa">${ex.ipa}</div>` : ""}
    <ol class="c-def">${ex.definicao.split(" · ").map((g) => html`<li>${g}</li>`)}</ol>
    <div class="c-frase">${destaque(ex.frase, ex.forma)}</div>
    <div class="c-trad">${ex.traducao}</div>
    <div class="c-meta">Formas mais comuns: ${ex.formas}<br>nº ${num(ex.rank)} em frequência · Tatoeba #${ex.frase_id}</div>
  </div>
</div>`
```

## Atualizações sem perder o histórico

Cada cartão tem um identificador fixo, calculado a partir da língua e da palavra. Quando os dados forem atualizados, baixe o baralho de novo e importe: o Anki reconhece os cartões que você já tem, atualiza o conteúdo e mantém o histórico de revisões. Se uma palavra mudar de faixa, o cartão continua no baralho onde já está.

<div class="tip">Quer só verbos, só substantivos ou uma faixa diferente? Em <a href="./palavras">Palavras</a> você filtra a lista e exporta a seleção num arquivo de texto que o Anki importa.</div>

<style>
.baralhos ul { list-style: none; padding: 0; margin: 0.5rem 0; }
.baralhos li { padding: 0.2rem 0; }
.cartoes { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 1rem; margin: 1rem 0; }
.cartao { background: #161615; border: 1px solid var(--theme-foreground-faintest); border-radius: 10px; padding: 1rem 1.2rem 1.4rem; text-align: center; color: #ecebe6; }
.rotulo { font: 600 11px var(--sans-serif); letter-spacing: 0.08em; text-transform: uppercase; color: var(--theme-foreground-faint); text-align: left; }
.c-palavra { font-size: 34px; font-weight: 600; margin-top: 0.6rem; }
.c-classe, .c-meta, .c-som { font-size: 13px; color: #9b9a95; }
.c-som { margin-top: 0.8rem; }
.c-ipa { color: #6da7ec; }
.c-def { text-align: left; padding-left: 1.3rem; font-size: 15px; }
.c-frase { font-size: 17px; margin-top: 0.6rem; }
.c-frase b { color: #6da7ec; }
.c-trad { font-size: 14px; color: #9b9a95; font-style: italic; }
.c-meta { margin-top: 0.8rem; }
.cartao hr { border: 0; border-top: 1px solid #3a3a37; margin: 0.8rem 0; }
</style>
