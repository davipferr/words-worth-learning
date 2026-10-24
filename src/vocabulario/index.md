---
title: "Vocabulário: visão geral"
toc: false
---

# Vocabulário: as palavras que valem a pena

<p class="lede">Quais palavras aprender primeiro em inglês, espanhol, francês, italiano, alemão, japonês e chinês? Contamos as palavras de centenas de milhões de falas de filmes e séries (OpenSubtitles), juntamos as formas de cada palavra ("estoy", "estaba", "estuvo" → <em>estar</em>) e ordenamos da mais útil para a menos útil. Cada lista vira um baralho do Anki.</p>

```js
import {parquet} from "../components/parquet.js";
import {LINGUAS, num, pct, rows} from "../components/format.js";
import {palette} from "../components/palette.js";
import {corLingua, curvas, legenda} from "../components/charts.js";

const cobertura = rows(await parquet(FileAttachment("../data/cobertura.parquet")));
const resumo = await FileAttachment("../data/resumo.json").json();
```

```js
const pal = palette(dark);
const cor = corLingua(pal);
const linguas = LINGUAS.filter((l) => resumo.linguas.some((r) => r.codigo === l.codigo));
const porCodigo = Object.fromEntries(resumo.linguas.map((r) => [r.codigo, r]));
const em1000 = resumo.linguas.map((r) => r.cobertura_em["1000"]);
const para90 = resumo.linguas.map((r) => r.para["90"]).filter((d) => d != null);
// Languages whose 10,000 most frequent words don't reach 90% (Chinese).
const sem90 = resumo.linguas.filter((r) => r.para["90"] == null).map((r) => LINGUAS.find((l) => l.codigo === r.codigo)?.nome.toLowerCase());
```

<div class="card hero">
  <h2 class="hero-title">Com as 1.000 palavras mais frequentes você reconhece de ${pct(d3.min(em1000))} a ${pct(d3.max(em1000))} de tudo o que se fala em filmes e séries. Chegar a 90% custa entre ${num(d3.min(para90))} e ${num(d3.max(para90))} palavras${sem90.length ? `; em ${sem90.join(" e ")}, mais de 10.000` : ""}.</h2>
  ${legenda(pal, linguas)}
  ${resize((width) => curvas(cobertura, {width, pal, linguas, alvo: 0.9, height: Math.min(420, Math.max(280, width * 0.45))}))}
  <p class="muted small">Cada linha mostra, para as N palavras mais frequentes de uma língua (eixo em escala logarítmica), a parcela de todas as palavras ditas nas legendas que elas cobrem. Linha tracejada: 90%. Nomes próprios e palavras que o Wiktionary não conhece nunca contam como "aprendidos". <a href="./cobertura">Mais sobre a cobertura →</a></p>
</div>

```js
// One card per language; the click remembers the language for the Palavras page.
html`<div class="grid grid-cols-${Math.min(linguas.length, 4)}">${linguas.map((l) => {
  const r = porCodigo[l.codigo];
  const lembrar = () => {
    try {
      sessionStorage.setItem("lingua", l.codigo);
    } catch {}
  };
  return html`<a class="card card-link" href="./palavras" onclick=${lembrar}>
    <h2><i class="dot" style=${{background: cor[l.codigo]}}></i>${l.nome}</h2>
    ${r.para["90"] != null
      ? html`<span class="big">${num(r.para["90"])}</span>
        <p class="muted">palavras para reconhecer 90% do que se fala; ${num(r.para["80"])} para 80%</p>`
      : // The ranking stops at 10,000 words: say how far those go instead.
        html`<span class="big">+10.000</span>
        <p class="muted">palavras para reconhecer 90% do que se fala: as 10.000 mais frequentes chegam a ${pct(r.cobertura_em["10000"])}; ${num(r.para["80"])} para 80%</p>`}
    <p class="muted small">${r.fonte === "wordfreq" ? "frequências do wordfreq (legendas, Wikipédia, notícias)" : `${num(r.tokens / 1e6)} milhões de palavras nas legendas`} · ${num(r.com_frase)} das ${num(resumo.palavras_por_lingua)} palavras com frase de exemplo</p>
  </a>`;
})}</div>`
```

<div class="grid grid-cols-2">
  <div class="card">
    <h3>Estude no Anki</h3>
    <p>Cada língua tem ${num(resumo.palavras_por_lingua)} palavras em ${resumo.linguas[0].baralhos.length} baralhos por faixa de frequência (1–500, 501–1.000…), com pronúncia, definições do Wiktionary, as formas mais comuns e uma frase de exemplo com tradução. Os cartões têm identificadores fixos: baixar de novo atualiza os seus cartões sem duplicar nem perder o histórico. <a href="./anki">Baixar os baralhos →</a></p>
  </div>
  <div class="card">
    <h3>Monte a sua própria lista</h3>
    <p>Em <a href="./palavras">Palavras</a>, filtre por classe (só verbos, só substantivos…), faixa de frequência ou busca, veja as frases de exemplo e exporte a seleção num arquivo de texto que o Anki importa. Os dados também podem ser consultados com <a href="../sql">SQL no navegador</a>.</p>
  </div>
</div>

<p class="muted small">Dados gerados em ${new Date(resumo.gerado_em).toLocaleString("pt-BR")}. <a href="../sobre">Metodologia e fontes</a>.</p>

<style>
.lede { font-size: 1.15rem; max-width: 52rem; color: var(--theme-foreground-muted); }
.card-link { text-decoration: none; color: inherit; transition: border-color 150ms, transform 150ms, box-shadow 150ms; }
.card-link:hover { border-color: var(--theme-foreground-focus); transform: translateY(-2px); box-shadow: 0 6px 18px rgba(0, 0, 0, 0.35); }
.card-link:focus-visible { outline: 2px solid var(--theme-foreground-focus); outline-offset: 2px; }
.card-link h2::after { content: "→"; display: inline-block; margin-left: 0.35em; color: var(--theme-foreground-focus); transition: transform 150ms; }
.card-link:hover h2::after { transform: translateX(3px); }
@media (prefers-reduced-motion: reduce) { .card-link, .card-link h2::after { transition: none; } .card-link:hover { transform: none; } }
.card .big { font-size: 28px; }
.dot { display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin-right: 0.45rem; }
.hero { padding: 1.5rem; }
.hero .hero-title { font: 600 clamp(19px, 2.4vw, 26px)/1.3 var(--serif); max-width: 52rem; margin-bottom: 1rem; color: var(--theme-foreground); }
</style>
