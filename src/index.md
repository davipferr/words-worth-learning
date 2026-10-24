---
toc: false
---

# Palavras que valem a pena

<p class="lede">Quais palavras aprender primeiro, e quanto do que você já sabe serve para a próxima língua? Contamos as palavras de centenas de milhões de falas de filmes e séries em inglês, espanhol, francês, italiano, alemão, japonês e chinês, e comparamos o vocabulário das sete línguas com o português.</p>

```js
import {parquet} from "./components/parquet.js";
import {num, pct, rows} from "./components/format.js";

const resumo = await FileAttachment("data/resumo.json").json();
const vantagem = rows(await parquet(FileAttachment("data/poliglota/vantagem.parquet")));
```

```js
const em1000 = resumo.linguas.map((r) => r.cobertura_em["1000"]);
const doPt = vantagem.filter((d) => d.origem === "pt").sort((a, b) => b.reconhecivel - a.reconhecivel);
const nome = {en: "inglês", es: "espanhol", fr: "francês", it: "italiano", de: "alemão", ja: "japonês", zh: "chinês"};
```

<div class="grid grid-cols-2">
  <a class="card card-link" href="./vocabulario/">
    <h2>Vocabulário</h2>
    <p class="muted">As ${num(resumo.palavras_por_lingua)} palavras mais frequentes de cada língua, da mais útil para a menos útil, com definições, pronúncia, frases de exemplo e baralhos para o Anki.</p>
    <span class="big">${pct(d3.min(em1000))}–${pct(d3.max(em1000))}</span>
    <p>de tudo o que se fala em filmes e séries é coberto pelas <strong>1.000 palavras mais frequentes</strong> de cada língua.</p>
  </a>
  <a class="card card-link" href="./poliglota/">
    <h2>Poliglota</h2>
    <p class="muted">O mesmo conceito nas sete línguas e no português: quais palavras são iguais, parecidas, de mesma origem ou falsos amigos.</p>
    <span class="big">${pct(doPt[0].reconhecivel)}</span>
    <p>do que se fala em <strong>${nome[doPt[0].alvo]}</strong> já é reconhecível para quem fala português; no ${nome[doPt.at(-1).alvo]}, só ${pct(doPt.at(-1).reconhecivel)}.</p>
  </a>
</div>

<p class="muted small">Dados gerados em ${new Date(resumo.gerado_em).toLocaleString("pt-BR")}. <a href="./sobre">Metodologia e fontes</a> · <a href="./sql">Consulta SQL</a>.</p>

<style>
.lede { font-size: 1.15rem; max-width: 52rem; color: var(--theme-foreground-muted); }
.card-link { text-decoration: none; color: inherit; transition: border-color 150ms, transform 150ms, box-shadow 150ms; }
.card-link:hover { border-color: var(--theme-foreground-focus); transform: translateY(-2px); box-shadow: 0 6px 18px rgba(0, 0, 0, 0.35); }
.card-link:focus-visible { outline: 2px solid var(--theme-foreground-focus); outline-offset: 2px; }
.card-link h2::after { content: "→"; display: inline-block; margin-left: 0.35em; color: var(--theme-foreground-focus); transition: transform 150ms; }
.card-link:hover h2::after { transform: translateX(3px); }
@media (prefers-reduced-motion: reduce) { .card-link, .card-link h2::after { transition: none; } .card-link:hover { transform: none; } }
.card .big { font-size: 34px; }
.card h2 { font: 600 22px var(--serif); }
</style>
