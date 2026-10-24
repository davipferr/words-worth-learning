---
title: "Poliglota: visão geral"
toc: false
---

# Poliglota: o que uma língua dá da outra

<p class="lede">Quem fala português já reconhece boa parte do espanhol sem estudar. E do italiano, do francês, do alemão? Alinhamos as 5.000 palavras mais frequentes do inglês com as suas equivalentes nas outras línguas e medimos, pelo que se fala em filmes e séries, quanto de cada língua é reconhecível a partir de outra.</p>

```js
import {parquet} from "../components/parquet.js";
import {num, pct, rows} from "../components/format.js";
import {palette} from "../components/palette.js";
import {matriz, NOMES} from "../components/poliglota.js";

const vantagem = rows(await parquet(FileAttachment("../data/poliglota/vantagem.parquet")));
const conceitos = rows(await parquet(FileAttachment("../data/poliglota/conceitos.parquet")));
const falsos = rows(await parquet(FileAttachment("../data/poliglota/falsos-amigos.parquet")));
const pal = palette(dark);
```

```js
const doPt = vantagem.filter((d) => d.origem === "pt").sort((a, b) => b.reconhecivel - a.reconhecivel);
const melhor = vantagem.filter((d) => d.origem !== "pt").sort((a, b) => b.reconhecivel - a.reconhecivel)[0];
const deEn = vantagem.find((d) => d.origem === "en" && d.alvo === "de");
const completos = conceitos.filter((d) => d.palavra_pt && d.n_linguas === 4).length;
```

<div class="card hero">
  <h2 class="hero-title">Para quem fala português, ${pct(doPt[0].reconhecivel)} do que se fala em ${NOMES[doPt[0].alvo].toLowerCase()} são palavras iguais ou parecidas com as nossas; no italiano, ${pct(doPt.find((d) => d.alvo === "it").reconhecivel)}; no francês, ${pct(doPt.find((d) => d.alvo === "fr").reconhecivel)}. No inglês e no alemão, só ${pct(doPt.find((d) => d.alvo === "en").reconhecivel)} e ${pct(doPt.find((d) => d.alvo === "de").reconhecivel)}.</h2>
  ${resize((width) => matriz(vantagem, {width, pal, destaque: (d) => d.origem === "pt"}))}
  <p class="muted small">Cada célula: parcela de todas as palavras ditas nas legendas da língua da coluna que são iguais ou parecidas com a palavra equivalente na língua da linha, contando só as 5.000 mais frequentes. É um piso: palavras sem equivalente alinhado contam como não reconhecidas. Passe o mouse para ver o detalhe. <a href="./vantagem">Mais sobre a vantagem →</a></p>
</div>

<div class="grid grid-cols-3">
  <a class="card card-link" href="./vantagem">
    <h2>Vantagem de partida</h2>
    <span class="big">${pct(melhor.reconhecivel)}</span>
    <p class="muted">do ${NOMES[melhor.alvo].toLowerCase()} é reconhecível para quem já sabe ${NOMES[melhor.origem].toLowerCase()}, o par mais próximo entre as línguas estrangeiras. Inglês e alemão, germânicos, se ajudam: ${pct(deEn.reconhecivel)} do alemão a partir do inglês.</p>
  </a>
  <a class="card card-link" href="./conceitos">
    <h2>Conceitos lado a lado</h2>
    <span class="big">${num(completos)}</span>
    <p class="muted">conceitos com palavra nas seis línguas, coloridos pela semelhança com o português. Também em baralho do Anki com as cinco línguas no verso.</p>
  </a>
  <a class="card card-link" href="./falsos-amigos">
    <h2>Falsos amigos</h2>
    <span class="big">${num(falsos.length)}</span>
    <p class="muted">pares de palavras escritas igual em duas línguas com sentidos diferentes, como <em>pain</em> (dor em inglês, pão em francês).</p>
  </a>
</div>

<div class="note">Nada aqui é traduzido pelo site: as palavras equivalentes vêm das tabelas de tradução do Wiktionary em inglês e só são aceitas quando a definição da própria palavra confirma o sentido. Veja o método em <a href="../sobre#poliglota">Sobre os dados</a>.</div>

<style>
.lede { font-size: 1.15rem; max-width: 52rem; color: var(--theme-foreground-muted); }
.card-link { text-decoration: none; color: inherit; transition: border-color 150ms, transform 150ms; }
.card-link:hover { border-color: var(--theme-foreground-focus); transform: translateY(-2px); }
.card-link h2::after { content: "→"; margin-left: 0.35em; color: var(--theme-foreground-focus); }
@media (prefers-reduced-motion: reduce) { .card-link { transition: none; } .card-link:hover { transform: none; } }
.card .big { font-size: 28px; }
.hero { padding: 1.5rem; }
.hero .hero-title { font: 600 clamp(19px, 2.4vw, 25px)/1.3 var(--serif); max-width: 52rem; margin-bottom: 1rem; color: var(--theme-foreground); }
</style>
